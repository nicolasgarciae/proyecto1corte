#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/nicolas/proyecto1corte"
ENV_FILE="$PROJECT_DIR/.env"
APP_LOG="/tmp/proyecto1corte-app.log"
RABBIT_UI_LOG="/tmp/proyecto1corte-rabbitmq-ui.log"
REDIS_UI_LOG="/tmp/proyecto1corte-redis-commander-ui.log"
DOZZLE_UI_LOG="/tmp/proyecto1corte-dozzle-ui.log"
PORTAINER_UI_LOG="/tmp/proyecto1corte-portainer-ui.log"

echo "[0/9] Verificando .env..."
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
    echo "  .env no existia, creado desde .env.example con valores por defecto."
    echo "  Edita $ENV_FILE para usar contrasenas seguras."
  else
    echo "  AVISO: no se encontro .env ni .env.example. Se usaran los defaults del docker-compose.yml."
  fi
fi

echo "[1/9] Iniciando MariaDB..."
service mariadb start >/dev/null 2>&1 || true

echo "[2/9] Iniciando Docker..."
service docker start >/dev/null 2>&1 || dockerd >/tmp/dockerd-codex.log 2>&1 &
sleep 6

echo "[3/9] Liberando puertos locales de paneles..."
pkill -f 'tcp_bridge.py :: 15673' || true
pkill -f 'tcp_bridge.py :: 8082' || true
pkill -f 'tcp_bridge.py :: 8083' || true
pkill -f 'tcp_bridge.py :: 9443' || true
pkill -f uvicorn || true
sleep 1

echo "[4/9] Construyendo imagen y levantando contenedores..."
cd "$PROJECT_DIR"
DOCKER_BUILDKIT=0 docker build -t proyecto1corte-api:local .
DOCKER_IMAGE=proyecto1corte-api:local docker compose up -d

echo "[5/9] Sincronizando .env con IPs reales de Docker..."
redis_ip="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' proyecto1corte-redis)"
rabbitmq_ip="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' proyecto1corte-rabbitmq)"
redis_commander_ip="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' proyecto1corte-redis-commander)"
dozzle_ip="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' proyecto1corte-dozzle)"
portainer_ip="$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' proyecto1corte-portainer)"

python3 - <<PY
from pathlib import Path
env_path = Path("$ENV_FILE")
lines = env_path.read_text().splitlines() if env_path.exists() else []
mapping = {}
for line in lines:
    if "=" in line and not line.strip().startswith("#"):
        key, value = line.split("=", 1)
        mapping[key] = value

mapping["MYSQL_HOST"] = mapping.get("MYSQL_HOST", "localhost")
mapping["MYSQL_PORT"] = mapping.get("MYSQL_PORT", "3306")
mapping["MYSQL_USER"] = mapping.get("MYSQL_USER", "api_user")
mapping["MYSQL_PASSWORD"] = mapping.get("MYSQL_PASSWORD", "123456")
mapping["MYSQL_DB"] = mapping.get("MYSQL_DB", "transporte_db")
mapping["REDIS_URL"] = "redis://$redis_ip:6379/0"
mapping["RABBITMQ_URL"] = "amqp://guest:guest@$rabbitmq_ip:5672/"
mapping["RABBITMQ_QUEUE"] = mapping.get("RABBITMQ_QUEUE", "reservas_eventos")

ordered = [
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DB",
    "REDIS_URL",
    "RABBITMQ_URL",
    "RABBITMQ_QUEUE",
]
# Preservar cualquier otra clave (SMTP_*, etc.) que ya estuviera en .env
extra = [k for k in mapping if k not in ordered]
all_keys = ordered + extra
env_path.write_text("\\n".join(f"{key}={mapping[key]}" for key in all_keys) + "\\n")
print(env_path.read_text(), end="")
PY

echo "[6/9] Esperando servicios internos..."
python3 - <<PY
import socket
import time

checks = [
    ("Redis", "$redis_ip", 6379),
    ("RabbitMQ", "$rabbitmq_ip", 5672),
    ("Redis Commander", "$redis_commander_ip", 8081),
    ("Dozzle", "$dozzle_ip", 8080),
    ("Portainer", "$portainer_ip", 9443),
]
pending = checks[:]
deadline = time.time() + 45

while pending and time.time() < deadline:
    still_pending = []
    for name, host, port in pending:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except OSError:
            still_pending.append((name, host, port))
    pending = still_pending
    if pending:
        time.sleep(2)

if pending:
    names = ", ".join(name for name, _, _ in pending)
    raise SystemExit(f"Servicios no disponibles a tiempo: {names}")
PY

echo "[7/9] Publicando paneles para Windows..."
nohup python3 "$PROJECT_DIR/tcp_bridge.py" :: 15673 "$rabbitmq_ip" 15672 >"$RABBIT_UI_LOG" 2>&1 &
nohup python3 "$PROJECT_DIR/tcp_bridge.py" :: 8082 "$redis_commander_ip" 8081 >"$REDIS_UI_LOG" 2>&1 &
nohup python3 "$PROJECT_DIR/tcp_bridge.py" :: 8083 "$dozzle_ip" 8080 >"$DOZZLE_UI_LOG" 2>&1 &
nohup python3 "$PROJECT_DIR/tcp_bridge.py" :: 9443 "$portainer_ip" 9443 >"$PORTAINER_UI_LOG" 2>&1 &
sleep 2

echo "[8/9] Esperando la app en el contenedor..."
python3 - <<'PY'
import socket
import time

deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", 8014), timeout=2):
            break
    except OSError:
        time.sleep(2)
else:
    raise SystemExit("La app no estuvo disponible a tiempo en el puerto 8014")
PY

echo "[9/9] Verificando servicios..."
echo "--- App ---"
curl -sS --max-time 10 http://127.0.0.1:8014/health || true
echo
echo "--- RabbitMQ UI ---"
curl -I -g --max-time 10 http://[::1]:15673/ || true
echo "--- Redis Commander UI ---"
curl -I -g --max-time 10 http://[::1]:8082/ || true
echo "--- Dozzle UI ---"
curl -I -g --max-time 10 http://[::1]:8083/ || true
echo "--- Portainer UI ---"
curl -k -I -g --max-time 10 https://[::1]:9443/ || true
echo "--- Login admin ---"
python3 - <<'PY'
import json
import urllib.request
base = "http://127.0.0.1:8014"
req = urllib.request.Request(
    base + "/auth/login",
    data=json.dumps({"username": "admin", "password": "admin"}).encode(),
    method="POST",
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=10) as resp:
    print(resp.status)
    print(resp.read().decode())
PY
echo "--- Infra ---"
python3 - <<'PY'
import json
import urllib.request
base = "http://127.0.0.1:8014"
login_req = urllib.request.Request(
    base + "/auth/login",
    data=json.dumps({"username": "admin", "password": "admin"}).encode(),
    method="POST",
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(login_req, timeout=10) as resp:
    token = json.loads(resp.read().decode())["token"]
infra_req = urllib.request.Request(base + "/infra/status", headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(infra_req, timeout=10) as resp:
    print(resp.read().decode())
PY
echo "--- Docker ---"
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
echo "--- App log ---"
docker logs --tail 40 proyecto1corte-app || true
