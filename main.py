import hashlib
import json
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aio_pika
import aiomysql
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import RABBITMQ_QUEUE, RABBITMQ_URL, REDIS_URL, get_connection
from logging_config import configure_logging

INDEX_FILE = Path(__file__).with_name("index.html")
CACHE_TTL = 30
SESSION_TTL_SECONDS = 60 * 60 * 12
ADMIN_EVENT_KEY = "admin:eventos"
ADMIN_EVENT_LIMIT = 40
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

logger = configure_logging("api")


class Ruta(BaseModel):
    origen: str
    destino: str
    capacidad: int = Field(..., ge=1)


class RutaUpdate(BaseModel):
    origen: Optional[str] = None
    destino: Optional[str] = None
    capacidad: Optional[int] = Field(default=None, ge=1)


class Reserva(BaseModel):
    nombre_pasajero: Optional[str] = None
    ruta_id: str


class ReservaUpdate(BaseModel):
    nombre_pasajero: Optional[str] = None
    ruta_id: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=4, max_length=120)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=120)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = None
    app.state.rabbit_connection = None
    app.state.rabbit_channel = None
    app.state.local_sessions = {}

    await ensure_user_schema()

    try:
        redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
    except Exception as exc:
        logger.warning("Redis no disponible", extra={"extra_fields": {"error": str(exc)}})

    try:
        rabbit_connection = await aio_pika.connect_robust(RABBITMQ_URL)
        rabbit_channel = await rabbit_connection.channel()
        await rabbit_channel.declare_queue(RABBITMQ_QUEUE, durable=True)
        app.state.rabbit_connection = rabbit_connection
        app.state.rabbit_channel = rabbit_channel
    except Exception as exc:
        logger.warning("RabbitMQ no disponible", extra={"extra_fields": {"error": str(exc)}})

    yield

    if app.state.redis is not None:
        await app.state.redis.close()

    if app.state.rabbit_channel is not None and not app.state.rabbit_channel.is_closed:
        await app.state.rabbit_channel.close()

    if app.state.rabbit_connection is not None and not app.state.rabbit_connection.is_closed:
        await app.state.rabbit_connection.close()


app = FastAPI(title="API Reservas de Transporte", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


PUBLIC_OPENAPI_PATHS = {
    "/",
    "/health",
    "/auth/register",
    "/auth/login",
}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Pega aqui el token devuelto por /auth/login, sin escribir la palabra Bearer.",
    }

    for path, methods in openapi_schema.get("paths", {}).items():
        if path in PUBLIC_OPENAPI_PATHS:
            continue
        for operation in methods.values():
            operation.setdefault("security", [{"BearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.middleware("http")
async def log_http_request(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(
        "Solicitud recibida",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            }
        },
    )

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Solicitud con error",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            },
        )
        raise

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Solicitud completada",
        extra={
            "extra_fields": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            }
        },
    )
    return response


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_username(value: str) -> str:
    return normalize_text(value).lower()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def serialize_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def get_first_value(row):
    if isinstance(row, dict):
        return next(iter(row.values()))
    return row[0]


async def ensure_user_schema():
    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)
    try:
        await cursor.execute("SHOW TABLES LIKE 'users'")
        users_table = await cursor.fetchone()
        if not users_table:
            await cursor.execute(
                """
                CREATE TABLE users (
                    id VARCHAR(36) PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    full_name VARCHAR(100) NOT NULL,
                    password_hash VARCHAR(64) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        await cursor.execute("SHOW COLUMNS FROM reservas LIKE 'user_id'")
        user_id_column = await cursor.fetchone()
        if not user_id_column:
            await cursor.execute("ALTER TABLE reservas ADD COLUMN user_id VARCHAR(36) NULL")

        await cursor.execute("SELECT id FROM users WHERE username=%s", (ADMIN_USERNAME,))
        admin_user = await cursor.fetchone()
        if not admin_user:
            await cursor.execute(
                """
                INSERT INTO users (id, username, full_name, password_hash, role)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    ADMIN_USERNAME,
                    "Administrador",
                    hash_password(ADMIN_PASSWORD),
                    "admin",
                ),
            )

        await conn.commit()
    finally:
        await cursor.close()
        conn.close()


async def get_cached_json(request: Request, key: str):
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return None

    cached = await redis_client.get(key)
    if not cached:
        return None

    return json.loads(cached)


async def set_cached_json(request: Request, key: str, payload, ttl: int = CACHE_TTL):
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return

    await redis_client.set(key, json.dumps(payload), ex=ttl)


async def invalidate_cache(request: Request):
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return

    await redis_client.delete("rutas:list", "reservas:list", "admin:dashboard")


async def publish_event(request: Request, event_type: str, payload: dict):
    channel = getattr(request.app.state, "rabbit_channel", None)
    log_id = str(uuid.uuid4())
    if channel is None or channel.is_closed:
        logger.warning(
            "RabbitMQ no disponible para publicar evento",
            extra={
                "log_id": log_id,
                "extra_fields": {"event_type": event_type},
            },
        )
        return False

    message = {
        "log_id": log_id,
        "type": event_type,
        "payload": payload,
        "created_at": utc_now_iso(),
    }

    await channel.default_exchange.publish(
        aio_pika.Message(
            body=json.dumps(message).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=RABBITMQ_QUEUE,
    )
    logger.info(
        "Evento publicado",
        extra={
            "log_id": log_id,
            "extra_fields": {"event_type": event_type, "queue": RABBITMQ_QUEUE},
        },
    )
    return True


def get_session_key(token: str) -> str:
    return f"session:{token}"


async def store_session(app: FastAPI, user: dict) -> str:
    token = secrets.token_urlsafe(32)
    payload = serialize_user(user)
    payload["created_at"] = utc_now_iso()

    redis_client = getattr(app.state, "redis", None)
    if redis_client is not None:
        await redis_client.set(get_session_key(token), json.dumps(payload), ex=SESSION_TTL_SECONDS)
    else:
        app.state.local_sessions[token] = payload

    return token


async def get_session(app: FastAPI, token: str):
    redis_client = getattr(app.state, "redis", None)
    if redis_client is not None:
        raw = await redis_client.get(get_session_key(token))
        if not raw:
            return None
        await redis_client.expire(get_session_key(token), SESSION_TTL_SECONDS)
        return json.loads(raw)

    return app.state.local_sessions.get(token)


async def delete_session(app: FastAPI, token: str):
    redis_client = getattr(app.state, "redis", None)
    if redis_client is not None:
        await redis_client.delete(get_session_key(token))
        return

    app.state.local_sessions.pop(token, None)


def extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


async def require_user(request: Request):
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Debes iniciar sesion para continuar")

    session = await get_session(request.app, token)
    if not session:
        raise HTTPException(status_code=401, detail="Tu sesion ya no es valida")

    return session


async def require_admin(request: Request):
    user = await require_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador puede realizar esta accion")
    return user


async def get_user_by_username(conn, username: str):
    cursor = await conn.cursor(aiomysql.DictCursor)
    try:
        await cursor.execute(
            "SELECT id, username, full_name, password_hash, role FROM users WHERE username=%s",
            (username,),
        )
        return await cursor.fetchone()
    finally:
        await cursor.close()


async def get_routes_with_stats(conn) -> list[dict]:
    cursor = await conn.cursor(aiomysql.DictCursor)
    try:
        await cursor.execute(
            """
            SELECT rutas.id,
                   rutas.origen,
                   rutas.destino,
                   rutas.capacidad,
                   COUNT(reservas.id) AS reservas_actuales
            FROM rutas
            LEFT JOIN reservas ON reservas.ruta_id = rutas.id
            GROUP BY rutas.id, rutas.origen, rutas.destino, rutas.capacidad
            ORDER BY rutas.origen, rutas.destino
            """
        )
        rutas = await cursor.fetchall()
    finally:
        await cursor.close()

    for ruta in rutas:
        reservas_actuales = int(ruta.get("reservas_actuales", 0) or 0)
        capacidad = int(ruta["capacidad"])
        ruta["reservas_actuales"] = reservas_actuales
        ruta["asientos_disponibles"] = max(capacidad - reservas_actuales, 0)
        ruta["ocupacion_porcentaje"] = round((reservas_actuales / capacidad) * 100, 2) if capacidad else 0

    return rutas


async def get_reservations(conn) -> list[dict]:
    cursor = await conn.cursor(aiomysql.DictCursor)
    try:
        await cursor.execute(
            """
            SELECT reservas.id,
                   reservas.nombre_pasajero,
                   reservas.ruta_id,
                   reservas.user_id,
                   rutas.origen,
                   rutas.destino,
                   users.username AS usuario_reserva,
                   users.full_name AS nombre_usuario
            FROM reservas
            JOIN rutas ON reservas.ruta_id = rutas.id
            LEFT JOIN users ON reservas.user_id = users.id
            ORDER BY reservas.nombre_pasajero, rutas.origen, rutas.destino
            """
        )
        return await cursor.fetchall()
    finally:
        await cursor.close()


async def get_route_capacity(cursor, ruta_id: str, exclude_reserva_id: Optional[str] = None):
    await cursor.execute("SELECT capacidad, origen, destino FROM rutas WHERE id=%s FOR UPDATE", (ruta_id,))
    ruta = await cursor.fetchone()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    params = [ruta_id]
    count_query = "SELECT COUNT(*) AS total FROM reservas WHERE ruta_id=%s"
    if exclude_reserva_id:
        count_query += " AND id <> %s"
        params.append(exclude_reserva_id)

    await cursor.execute(count_query, tuple(params))
    total = await cursor.fetchone()
    return ruta, int(get_first_value(total))


@app.get("/")
async def home():
    if not INDEX_FILE.exists():
        raise HTTPException(status_code=404, detail="No se encontro index.html")
    return FileResponse(INDEX_FILE)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/auth/register")
async def register_user(payload: RegisterRequest, request: Request):
    username = normalize_username(payload.username)
    full_name = normalize_text(payload.full_name)

    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)
    user_id = str(uuid.uuid4())

    try:
        await cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        existing = await cursor.fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Ese usuario ya existe")

        await cursor.execute(
            """
            INSERT INTO users (id, username, full_name, password_hash, role)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, username, full_name, hash_password(payload.password), "user"),
        )
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    user = {
        "id": user_id,
        "username": username,
        "full_name": full_name,
        "role": "user",
    }
    token = await store_session(request.app, user)
    return {"token": token, "user": user}


@app.post("/auth/login")
async def login_user(payload: LoginRequest, request: Request):
    username = normalize_username(payload.username)
    conn = await get_connection()
    try:
        user = await get_user_by_username(conn, username)
    finally:
        conn.close()

    if not user or user["password_hash"] != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    token = await store_session(request.app, user)
    return {"token": token, "user": serialize_user(user)}


@app.get("/auth/me")
async def get_current_session(request: Request):
    user = await require_user(request)
    return {"user": user}


@app.post("/auth/logout")
async def logout_user(request: Request):
    token = extract_bearer_token(request)
    if token:
        await delete_session(request.app, token)
    return {"mensaje": "Sesion cerrada"}


@app.get("/infra/status")
async def infra_status(request: Request):
    await require_admin(request)

    mysql_ok = False
    try:
        conn = await get_connection()
        cursor = await conn.cursor()
        await cursor.execute("SELECT 1")
        await cursor.fetchone()
        await cursor.close()
        conn.close()
        mysql_ok = True
    except Exception:
        mysql_ok = False

    redis_client = getattr(request.app.state, "redis", None)
    redis_ok = False
    if redis_client is not None:
        try:
            redis_ok = bool(await redis_client.ping())
        except Exception:
            redis_ok = False

    rabbit_channel = getattr(request.app.state, "rabbit_channel", None)
    rabbit_ok = bool(rabbit_channel is not None and not rabbit_channel.is_closed)

    return {
        "mysql": mysql_ok,
        "redis": redis_ok,
        "rabbitmq": rabbit_ok,
        "queue": RABBITMQ_QUEUE,
    }


@app.post("/rutas")
async def crear_ruta(ruta: Ruta, request: Request):
    admin_user = await require_admin(request)

    conn = await get_connection()
    cursor = await conn.cursor()
    ruta_id = str(uuid.uuid4())

    try:
        await cursor.execute(
            """
            INSERT INTO rutas (id, origen, destino, capacidad)
            VALUES (%s, %s, %s, %s)
            """,
            (ruta_id, normalize_text(ruta.origen), normalize_text(ruta.destino), ruta.capacidad),
        )
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(
        request,
        "ruta_creada",
        {
            "id": ruta_id,
            "origen": normalize_text(ruta.origen),
            "destino": normalize_text(ruta.destino),
            "capacidad": ruta.capacidad,
            "actor": admin_user["username"],
        },
    )

    return {"mensaje": "Ruta creada", "id": ruta_id}


@app.get("/rutas")
async def obtener_rutas(request: Request):
    cached = await get_cached_json(request, "rutas:list")
    if cached is not None:
        return cached

    conn = await get_connection()
    try:
        rutas = await get_routes_with_stats(conn)
    finally:
        conn.close()

    await set_cached_json(request, "rutas:list", rutas)
    return rutas


@app.patch("/rutas/{ruta_id}")
async def actualizar_ruta(ruta_id: str, ruta: RutaUpdate, request: Request):
    admin_user = await require_admin(request)
    payload = {key: value for key, value in ruta.dict(exclude_unset=True).items() if value is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un campo para actualizar")

    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)

    try:
        await cursor.execute(
            """
            SELECT rutas.id,
                   rutas.origen,
                   rutas.destino,
                   rutas.capacidad,
                   COUNT(reservas.id) AS reservas_actuales
            FROM rutas
            LEFT JOIN reservas ON reservas.ruta_id = rutas.id
            WHERE rutas.id=%s
            GROUP BY rutas.id, rutas.origen, rutas.destino, rutas.capacidad
            """,
            (ruta_id,),
        )
        actual = await cursor.fetchone()
        if not actual:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")

        nueva_capacidad = payload.get("capacidad", actual["capacidad"])
        if nueva_capacidad < int(actual["reservas_actuales"]):
            raise HTTPException(
                status_code=400,
                detail="La capacidad no puede ser menor que las reservas actuales",
            )

        fields = []
        values = []
        for key in ("origen", "destino", "capacidad"):
            if key in payload:
                fields.append(f"{key}=%s")
                values.append(normalize_text(payload[key]) if isinstance(payload[key], str) else payload[key])

        values.append(ruta_id)
        await cursor.execute(f"UPDATE rutas SET {', '.join(fields)} WHERE id=%s", tuple(values))
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(request, "ruta_actualizada", {"id": ruta_id, **payload, "actor": admin_user["username"]})
    return {"mensaje": "Ruta actualizada", "id": ruta_id}


@app.delete("/rutas/{ruta_id}")
async def eliminar_ruta(ruta_id: str, request: Request):
    admin_user = await require_admin(request)
    conn = await get_connection()
    cursor = await conn.cursor()

    try:
        await cursor.execute("SELECT COUNT(*) FROM reservas WHERE ruta_id=%s", (ruta_id,))
        reservas_asociadas = await cursor.fetchone()
        if reservas_asociadas[0] > 0:
            raise HTTPException(
                status_code=400,
                detail="Primero debes cancelar las reservas asociadas a esta ruta",
            )

        await cursor.execute("DELETE FROM rutas WHERE id=%s", (ruta_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")

        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(request, "ruta_eliminada", {"id": ruta_id, "actor": admin_user["username"]})
    return {"mensaje": "Ruta eliminada", "id": ruta_id}


@app.post("/reservas")
async def crear_reserva(reserva: Reserva, request: Request):
    current_user = await require_user(request)

    conn = await get_connection()
    cursor = await conn.cursor()
    reserva_id = str(uuid.uuid4())

    try:
        ruta, reservas_actuales = await get_route_capacity(cursor, reserva.ruta_id)
        capacidad = int(get_first_value(ruta))
        if reservas_actuales >= capacidad:
            raise HTTPException(status_code=400, detail="La ruta ha alcanzado su capacidad maxima")

        passenger_name = normalize_text(reserva.nombre_pasajero or current_user["full_name"] or current_user["username"])

        await cursor.execute(
            """
            INSERT INTO reservas (id, nombre_pasajero, ruta_id, user_id)
            VALUES (%s, %s, %s, %s)
            """,
            (reserva_id, passenger_name, reserva.ruta_id, current_user["id"]),
        )
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(
        request,
        "reserva_creada",
        {
            "id": reserva_id,
            "nombre_pasajero": passenger_name,
            "ruta_id": reserva.ruta_id,
            "actor": current_user["username"],
        },
    )

    return {"mensaje": "Reserva creada", "id": reserva_id}


@app.get("/reservas")
async def obtener_reservas(request: Request):
    await require_admin(request)
    cached = await get_cached_json(request, "reservas:list")
    if cached is not None:
        return cached

    conn = await get_connection()
    try:
        reservas = await get_reservations(conn)
    finally:
        conn.close()

    await set_cached_json(request, "reservas:list", reservas)
    return reservas


@app.patch("/reservas/{reserva_id}")
async def actualizar_reserva(reserva_id: str, reserva: ReservaUpdate, request: Request):
    admin_user = await require_admin(request)
    payload = {key: value for key, value in reserva.dict(exclude_unset=True).items() if value is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un campo para actualizar")

    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)

    try:
        await cursor.execute(
            "SELECT id, nombre_pasajero, ruta_id, user_id FROM reservas WHERE id=%s",
            (reserva_id,),
        )
        actual = await cursor.fetchone()
        if not actual:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")

        nueva_ruta_id = payload.get("ruta_id", actual["ruta_id"])
        if nueva_ruta_id != actual["ruta_id"]:
            ruta_data, reservas_actuales = await get_route_capacity(cursor, nueva_ruta_id, exclude_reserva_id=reserva_id)
            capacidad = int(get_first_value(ruta_data))
            if reservas_actuales >= capacidad:
                raise HTTPException(status_code=400, detail="La nueva ruta ya no tiene cupos disponibles")

        fields = []
        values = []
        for key in ("nombre_pasajero", "ruta_id"):
            if key in payload:
                fields.append(f"{key}=%s")
                values.append(normalize_text(payload[key]) if isinstance(payload[key], str) else payload[key])

        values.append(reserva_id)
        await cursor.execute(f"UPDATE reservas SET {', '.join(fields)} WHERE id=%s", tuple(values))
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(request, "reserva_actualizada", {"id": reserva_id, **payload, "actor": admin_user["username"]})
    return {"mensaje": "Reserva actualizada", "id": reserva_id}


@app.delete("/reservas/{reserva_id}")
async def eliminar_reserva(reserva_id: str, request: Request):
    admin_user = await require_admin(request)
    conn = await get_connection()
    cursor = await conn.cursor()

    try:
        await cursor.execute("DELETE FROM reservas WHERE id=%s", (reserva_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")
        await conn.commit()
    finally:
        await cursor.close()
        conn.close()

    await invalidate_cache(request)
    await publish_event(request, "reserva_cancelada", {"id": reserva_id, "actor": admin_user["username"]})
    return {"mensaje": "Reserva cancelada", "id": reserva_id}


@app.get("/admin/dashboard")
async def admin_dashboard(request: Request):
    await require_admin(request)
    cached = await get_cached_json(request, "admin:dashboard")
    if cached is not None:
        return cached

    conn = await get_connection()
    try:
        rutas = await get_routes_with_stats(conn)
        reservas = await get_reservations(conn)
    finally:
        conn.close()

    total_capacidad = sum(ruta["capacidad"] for ruta in rutas)
    total_reservas = len(reservas)
    total_disponibles = sum(ruta["asientos_disponibles"] for ruta in rutas)
    ocupacion_promedio = round((total_reservas / total_capacidad) * 100, 2) if total_capacidad else 0

    dashboard = {
        "metricas": {
            "total_rutas": len(rutas),
            "total_reservas": total_reservas,
            "capacidad_total": total_capacidad,
            "asientos_disponibles": total_disponibles,
            "ocupacion_promedio": ocupacion_promedio,
        },
        "rutas": rutas,
        "reservas": reservas,
    }

    await set_cached_json(request, "admin:dashboard", dashboard)
    return dashboard


@app.get("/admin/eventos")
async def admin_eventos(request: Request):
    await require_admin(request)
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return {"items": []}

    raw_items = await redis_client.lrange(ADMIN_EVENT_KEY, 0, ADMIN_EVENT_LIMIT - 1)
    items = []
    for raw in raw_items:
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    return {"items": items}
