#!/usr/bin/env python3
"""
Prueba de concurrencia para ReservaYa.

Escenario 1 (race condition):
    N usuarios intentan reservar EL MISMO asiento, misma ruta, misma fecha,
    al mismo tiempo. El indice unico (ruta_id, asiento, fecha_reserva) debe
    garantizar que solo 1 gane y el resto reciba 409.

Escenario 2 (carga):
    N usuarios reservan asientos DISTINTOS en paralelo. Mide throughput y
    verifica que la capacidad no se sobrepase.

Uso:
    python3 concurrency_test.py
    python3 concurrency_test.py --users 50 --url http://localhost:8014

Sin dependencias externas (solo stdlib).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

# ── Config por defecto ────────────────────────────────────────────────────────
DEFAULT_URL = "http://localhost:8014"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"


def http(method, url, body=None, token=None, timeout=15):
    """Request HTTP simple. Devuelve (status, json|texto)."""
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def login(url, username, password):
    status, body = http("POST", f"{url}/auth/login", {"username": username, "password": password})
    if status == 200 and isinstance(body, dict):
        return body["token"]
    return None


def register(url, username, full_name, email, password):
    status, body = http("POST", f"{url}/auth/register",
                        {"username": username, "full_name": full_name,
                         "email": email, "password": password})
    if status == 200 and isinstance(body, dict):
        return body["token"]
    return None


def ensure_route(url, admin_token, capacity=40):
    """Devuelve una ruta existente o crea una nueva."""
    status, rutas = http("GET", f"{url}/rutas", token=admin_token)
    if status == 200 and isinstance(rutas, list) and rutas:
        # buscar ruta con capacidad suficiente
        for r in rutas:
            if int(r.get("capacidad", 0)) >= capacity:
                return r
        return rutas[0]

    # crear ruta nueva
    status, body = http("POST", f"{url}/rutas", token=admin_token,
                        body={"origen": "CiudadTest A", "destino": "CiudadTest B",
                              "capacidad": capacity, "precio": 25000})
    if status == 200 and isinstance(body, dict):
        status, rutas = http("GET", f"{url}/rutas", token=admin_token)
        if status == 200 and rutas:
            return rutas[-1]
    print(f"  ERROR creando ruta: {status} {body}")
    sys.exit(1)


def index_to_seat(index):
    row = (index - 1) // 4
    col = ((index - 1) % 4) + 1
    return f"{chr(ord('A') + row)}{col}"


def make_users(url, n):
    """Registra n usuarios y devuelve lista de tokens."""
    print(f"[*] Registrando {n} usuarios de prueba...")
    tokens = []
    suffix = uuid.uuid4().hex[:6]

    def reg(i):
        uname = f"loadtest_{suffix}_{i}"
        return register(url, uname, f"Load Test {i}", f"{uname}@test.com", "test1234")

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(reg, range(n)))

    tokens = [t for t in results if t]
    print(f"    {len(tokens)}/{n} usuarios creados.")
    if not tokens:
        print("    ERROR: no se pudo crear ningun usuario.")
        sys.exit(1)
    return tokens


def reservar(url, token, ruta_id, fecha, seat, phone="3001234567", metodo="tarjeta"):
    t0 = time.perf_counter()
    status, body = http("POST", f"{url}/reservas", token=token,
                        body={"ruta_id": ruta_id, "telefono": phone,
                              "fecha_reserva": fecha, "asiento": seat,
                              "metodo_pago": metodo})
    dt = time.perf_counter() - t0
    return status, body, dt


# ── Escenario 1: race condition mismo asiento ─────────────────────────────────
def test_same_seat(url, tokens, ruta, fecha):
    seat = "A1"
    n = len(tokens)
    print(f"\n=== ESCENARIO 1: {n} usuarios, MISMO asiento {seat}, fecha {fecha} ===")
    print("    Esperado: exactamente 1 exito (201), el resto 409 conflicto.\n")

    results = []
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(reservar, url, tok, ruta["id"], fecha, seat) for tok in tokens]
        for f in as_completed(futures):
            results.append(f.result())

    ok = [r for r in results if r[0] == 200]
    conflict = [r for r in results if r[0] in (400, 409)]
    other = [r for r in results if r[0] not in (200, 400, 409)]

    print(f"    Exitos (200)      : {len(ok)}")
    print(f"    Conflictos (409)  : {len(conflict)}")
    print(f"    Otros / errores   : {len(other)}")
    if other:
        for s, b, _ in other[:5]:
            print(f"      -> status {s}: {b}")

    veredicto = "PASS ✓" if len(ok) == 1 else "FAIL ✗"
    print(f"\n    VEREDICTO: {veredicto}  (debe haber exactamente 1 exito)")
    return len(ok) == 1


# ── Escenario 2: asientos distintos en paralelo ───────────────────────────────
def test_distinct_seats(url, tokens, ruta, fecha):
    capacidad = int(ruta["capacidad"])
    n = min(len(tokens), capacidad)
    print(f"\n=== ESCENARIO 2: {n} usuarios, asientos DISTINTOS, fecha {fecha} ===")
    print(f"    Capacidad ruta: {capacidad}. Esperado: {n} exitos sin pasar capacidad.\n")

    seats = [index_to_seat(i) for i in range(1, n + 1)]

    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(reservar, url, tokens[i], ruta["id"], fecha, seats[i])
                   for i in range(n)]
        for f in as_completed(futures):
            results.append(f.result())
    total_time = time.perf_counter() - t0

    ok = [r for r in results if r[0] == 200]
    fail = [r for r in results if r[0] != 200]
    latencias = sorted(r[2] for r in results)
    p50 = latencias[len(latencias) // 2]
    p95 = latencias[int(len(latencias) * 0.95)]

    print(f"    Exitos            : {len(ok)}/{n}")
    print(f"    Fallos            : {len(fail)}")
    print(f"    Tiempo total      : {total_time:.2f}s")
    print(f"    Throughput        : {n / total_time:.1f} reservas/s")
    print(f"    Latencia p50      : {p50*1000:.0f} ms")
    print(f"    Latencia p95      : {p95*1000:.0f} ms")
    if fail:
        for s, b, _ in fail[:5]:
            print(f"      -> status {s}: {b}")

    veredicto = "PASS ✓" if len(ok) == n else "FAIL ✗"
    print(f"\n    VEREDICTO: {veredicto}  (todos deben reservar su asiento)")
    return len(ok) == n


def main():
    parser = argparse.ArgumentParser(description="Prueba de concurrencia ReservaYa")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL base de la API")
    parser.add_argument("--users", type=int, default=30, help="Numero de usuarios concurrentes")
    args = parser.parse_args()

    url = args.url.rstrip("/")
    print(f"[*] Objetivo: {url}")

    # health
    status, _ = http("GET", f"{url}/health")
    if status != 200:
        print(f"    ERROR: la API no responde en {url} (status {status})")
        sys.exit(1)
    print("    API viva.")

    # admin
    admin_token = login(url, ADMIN_USER, ADMIN_PASS)
    if not admin_token:
        print("    ERROR: no se pudo iniciar sesion como admin.")
        sys.exit(1)

    ruta = ensure_route(url, admin_token, capacity=max(args.users, 40))
    print(f"[*] Ruta de prueba: {ruta['origen']} -> {ruta['destino']} "
          f"(cap {ruta['capacidad']}, id {ruta['id'][:8]})")

    tokens = make_users(url, args.users)

    # fecha unica para no chocar con corridas previas
    fecha = (date.today() + timedelta(days=(int(time.time()) % 300) + 1)).isoformat()

    r1 = test_same_seat(url, tokens, ruta, fecha)

    fecha2 = (date.today() + timedelta(days=(int(time.time()) % 300) + 400)).isoformat()
    r2 = test_distinct_seats(url, tokens, ruta, fecha2)

    print("\n" + "=" * 50)
    print(f"RESUMEN:  Escenario 1 {'PASS' if r1 else 'FAIL'}  |  Escenario 2 {'PASS' if r2 else 'FAIL'}")
    print("=" * 50)
    sys.exit(0 if (r1 and r2) else 1)


if __name__ == "__main__":
    main()
