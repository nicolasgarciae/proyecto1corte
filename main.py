from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
import aiomysql


from database import get_connection

app = FastAPI(title="API Reservas de Transporte")

# ---------------- MODELOS ----------------

class Ruta(BaseModel):
    origen: str
    destino: str
    capacidad: int

class Reserva(BaseModel):
    nombre_pasajero: str
    ruta_id: str

# ---------------- ENDPOINTS ----------------

# Crear ruta
@app.post("/rutas")
async def crear_ruta(ruta: Ruta):

    conn = await get_connection()
    cursor = await conn.cursor()

    ruta_id = str(uuid.uuid4())

    query = """
    INSERT INTO rutas (id, origen, destino, capacidad)
    VALUES (%s, %s, %s, %s)
    """

    await cursor.execute(query, (ruta_id, ruta.origen, ruta.destino, ruta.capacidad))
    await conn.commit()

    await cursor.close()
    conn.close()

    return {
        "mensaje": "Ruta creada",
        "id": ruta_id
    }


# Obtener rutas
@app.get("/rutas")
async def obtener_rutas():

    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)

    query = "SELECT * FROM rutas"
    await cursor.execute(query)

    rutas = await cursor.fetchall()

    await cursor.close()
    conn.close()

    return rutas


# Crear reserva
@app.post("/reservas")
async def crear_reserva(reserva: Reserva):

    conn = await get_connection()
    cursor = await conn.cursor()

    reserva_id = str(uuid.uuid4())

    # Verificar que la ruta exista
    await cursor.execute("SELECT * FROM rutas WHERE id=%s", (reserva.ruta_id,))
    ruta = await cursor.fetchone()

    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    query = """
    INSERT INTO reservas (id, nombre_pasajero, ruta_id)
    VALUES (%s, %s, %s)
    """

    await cursor.execute(query, (reserva_id, reserva.nombre_pasajero, reserva.ruta_id))
    await conn.commit()

    await cursor.close()
    conn.close()

    return {
        "mensaje": "Reserva creada",
        "id": reserva_id
    }

# Obtener reservas
@app.get("/reservas")
async def obtener_reservas():

    conn = await get_connection()
    cursor = await conn.cursor(aiomysql.DictCursor)

    query = """
    SELECT reservas.id, reservas.nombre_pasajero, rutas.origen, rutas.destino
    FROM reservas
    JOIN rutas ON reservas.ruta_id = rutas.id
    """

    await cursor.execute(query)
    reservas = await cursor.fetchall()

    await cursor.close()
    conn.close()

    return reservas