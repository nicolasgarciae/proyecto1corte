# API Reservas de Transporte

Proyecto de reservas de transporte con FastAPI, MySQL, Redis, RabbitMQ, worker, Docker Compose, Portainer y Dozzle.

## Despliegue Rapido En Otra Maquina

Estos pasos permiten clonar y ejecutar el proyecto completo usando Docker. No necesitas instalar Python, MySQL, Redis ni RabbitMQ por separado.

### 1. Requisitos

En la maquina nueva debes tener:

- Git
- Docker
- Docker Compose
- WSL si estas en Windows

Verifica:

```bash
git --version
docker --version
docker compose version
```

### 2. Clonar el repositorio

```bash
git clone https://github.com/nicolasgarciae/proyecto1corte.git
cd proyecto1corte
```

Si estas en Windows, ejecuta estos comandos dentro de WSL.

### 3. Levantar el sistema completo

Opcion A: construir la imagen localmente desde el codigo clonado.

```bash
make up
```

Equivalente manual:

```bash
DOCKER_IMAGE=proyecto1corte-api:local docker compose build app
DOCKER_IMAGE=proyecto1corte-api:local docker compose up -d
```

Opcion B: usar la imagen publicada en DockerHub.

```bash
DOCKER_IMAGE=nicolasgarciae1/proyecto1corte-api:v1 docker compose up -d
```

Con Makefile:

```bash
make deploy DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1
```

### 4. Verificar que todo funciona

```bash
docker compose ps
curl http://127.0.0.1:8014/health
```

La respuesta esperada es:

```json
{"status":"ok"}
```

### 5. Abrir la aplicacion y paneles

- Aplicacion/API: `http://localhost:8014`
- RabbitMQ UI: `http://localhost:15673`
- Redis Commander: `http://localhost:8082`
- Dozzle logs: `http://localhost:8083`
- Portainer: `https://localhost:9443`

Credenciales de RabbitMQ:

- Usuario: `guest`
- Contrasena: `guest`

En Portainer, la primera vez debes crear el usuario administrador inicial. El navegador puede mostrar advertencia porque Portainer usa certificado HTTPS autofirmado.

### 6. Detener el sistema

```bash
docker compose down
```

Para detener y borrar volumenes de datos:

```bash
docker compose down -v
```

Usa `down -v` solo si quieres borrar la base de datos MySQL y datos persistentes.

## Servicios Docker

El `docker-compose.yml` levanta:

- `proyecto1corte-app`: API FastAPI en el puerto `8014`
- `proyecto1corte-worker`: consumer de RabbitMQ
- `proyecto1corte-mysql`: MySQL 8 en el puerto `3307`
- `proyecto1corte-redis`: Redis en el puerto `6380`
- `proyecto1corte-rabbitmq`: RabbitMQ AMQP en `5673` y panel en `15673`
- `proyecto1corte-redis-commander`: panel Redis en `8082`
- `proyecto1corte-dozzle`: visor de logs en `8083`
- `proyecto1corte-portainer`: administracion Docker en `9443`

Los contenedores se comunican por la red interna de Docker Compose usando los nombres `mysql`, `redis` y `rabbitmq`.

## Comandos Makefile

```bash
make help
make github-flow
make up
make down
make logs
make restart
make status
make build DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1
make push DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1
make deploy DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1
```

## Publicar Imagen En DockerHub

Primero inicia sesion:

```bash
docker login
```

Construye la imagen:

```bash
docker build -t nicolasgarciae1/proyecto1corte-api:v1 .
```

Sube la imagen:

```bash
docker push nicolasgarciae1/proyecto1corte-api:v1
```

Con Makefile:

```bash
make login
make push DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1
```

La imagen queda disponible como:

```text
nicolasgarciae1/proyecto1corte-api:v1
```

## GitHub Flow

Flujo recomendado para trabajar:

```bash
git checkout main
git pull origin main
git checkout -b feature-nombre-del-cambio
git add .
git commit -m "Descripcion del cambio"
git push -u origin feature-nombre-del-cambio
```

Luego abre un Pull Request hacia `main`, revisa los cambios y haz merge.

La guia completa de despliegue esta en `DEPLOYMENT.md`.

## Lo Que Incluye

- Login y registro de usuarios.
- Sesiones con token usando Redis.
- Credenciales fijas del administrador:
  - Usuario: `admin`
  - Contrasena: `admin`
- Panel administrador protegido por backend y frontend.
- Usuarios normales pueden ver rutas e iniciar sesion para hacer reservas.
- Redis para cache y sesiones.
- RabbitMQ para publicar eventos operativos.
- Worker para procesar la cola y guardar actividad reciente en Redis.
- Logs JSON con `log_id` UUID en API y worker.
- Dozzle para observar logs de contenedores.
- Portainer para ver servicios, contenedores, imagenes, volumenes y redes.

## Base De Datos

MySQL se levanta automaticamente con Docker. El archivo `docker/mysql/init.sql` crea las tablas base `rutas` y `reservas`.

La API tambien crea la tabla `users` automaticamente al arrancar y, si hace falta, agrega la columna `user_id` a `reservas`.

Credenciales internas usadas por Docker Compose:

```env
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=api_user
MYSQL_PASSWORD=123456
MYSQL_DB=transporte_db
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_QUEUE=reservas_eventos
```

## Endpoints Principales

- `GET /` interfaz web
- `GET /health` estado basico de la API
- `POST /auth/register` crear cuenta
- `POST /auth/login` iniciar sesion
- `GET /auth/me` validar sesion
- `POST /auth/logout` cerrar sesion
- `GET /rutas` listar rutas con ocupacion
- `POST /reservas` crear reserva con sesion iniciada
- `GET /admin/dashboard` panel admin
- `GET /admin/eventos` eventos procesados
- `GET /infra/status` estado de MySQL, Redis y RabbitMQ

## Solucion De Problemas

Si Docker no esta activo en WSL:

```bash
sudo dockerd
```

En otra terminal WSL, vuelve a ejecutar:

```bash
docker compose up -d --build
```

Si algun puerto esta ocupado, revisa:

```bash
docker compose ps
docker ps
```

Si quieres reiniciar desde cero:

```bash
docker compose down -v
make up
```


### Error: pull access denied for proyecto1corte-api

Si aparece este error al ejecutar `make start` o `docker compose up`, significa que Docker intento descargar la imagen local `proyecto1corte-api:local` antes de construirla.

Solucion:

```bash
DOCKER_IMAGE=proyecto1corte-api:local docker compose build app
DOCKER_IMAGE=proyecto1corte-api:local docker compose up -d
```

O simplemente usa:

```bash
make up
```
