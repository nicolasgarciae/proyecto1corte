# Despliegue: GitHub Flow + Docker + WSL

Esta configuracion sigue la guia de despliegue del curso para convertir el proyecto en un sistema distribuido desplegable.

## 1. GitHub Flow

`main` debe representar la version estable. Cada cambio nuevo se trabaja en una rama `feature-*` y se integra mediante Pull Request.

```bash
git checkout main
git pull origin main
git checkout -b feature-despliegue
git add .
git commit -m "Configurar despliegue con Docker y WSL"
git push -u origin feature-despliegue
```

Luego abre un Pull Request hacia `main`, revisa los cambios y haz merge cuando este aprobado.

## 2. Docker desde WSL

Desde la carpeta del proyecto:

```bash
cd /home/nicolas/proyecto1corte
make build DOCKER_USERNAME=tu_usuario_dockerhub IMAGE_TAG=v1
```

Esto construye la imagen:

```text
tu_usuario_dockerhub/proyecto1corte-api:v1
```

## 3. Publicar en DockerHub

```bash
make login
make push DOCKER_USERNAME=tu_usuario_dockerhub IMAGE_TAG=v1
```

Tambien puedes hacerlo manual:

```bash
docker build -t tu_usuario_dockerhub/proyecto1corte-api:v1 .
docker push tu_usuario_dockerhub/proyecto1corte-api:v1
```

## 4. Ejecutar en otra maquina

Instala Docker, clona el repositorio y ejecuta:

```bash
cd proyecto1corte
make deploy DOCKER_USERNAME=tu_usuario_dockerhub IMAGE_TAG=v1
```

El sistema levanta:

- `proyecto1corte-app`: API FastAPI en `http://localhost:8014`
- `proyecto1corte-worker`: consumer de RabbitMQ
- `proyecto1corte-mysql`: MySQL en `localhost:3307`
- `proyecto1corte-redis`: Redis en `localhost:6380`
- `proyecto1corte-rabbitmq`: RabbitMQ AMQP en `localhost:5673`
- `proyecto1corte-redis-commander`: panel Redis
- `proyecto1corte-dozzle`: logs Docker
- `proyecto1corte-portainer`: servicios activos Docker

## 5. GitHub Actions

El workflow esta en `.github/workflows/docker.yml`.

Configura estos secretos en GitHub:

- `DOCKER_USERNAME`: usuario de DockerHub
- `DOCKER_PASSWORD`: token o password de DockerHub

Comportamiento:

- En Pull Request hacia `main`: construye la imagen para validar que Docker funciona.
- En push a `main`: construye y publica la imagen en DockerHub como `v1` y `latest`.

## 6. Comandos utiles

```bash
make help
make github-flow
make up
make logs
make status
make down
```

## 7. Verificacion

```bash
docker ps
docker compose ps
curl http://127.0.0.1:8014/health
```

En Portainer puedes revisar los contenedores activos en:

```text
https://localhost:9443
```

Si usas `sudo ./start_all.sh`, el script publica los paneles auxiliares para Windows desde WSL.
