# ReservaYa — Sistema de Reservas de Transporte

API y panel web para reservas de buses, construido con FastAPI, MySQL, Redis y RabbitMQ. Todo corre en Docker, sin necesidad de instalar nada más.

---

## Despliegue en otra máquina (paso a paso)

> Sigue estos pasos **en orden**. Si algo falla, ve directo a la sección [Solución de problemas](#solución-de-problemas).

---

### Paso 1 — Instalar los requisitos

Necesitas tener instalados:

| Herramienta | Para qué sirve | Cómo instalar |
|---|---|---|
| **Git** | Descargar el código | https://git-scm.com/downloads |
| **Docker Desktop** | Correr todos los servicios | https://www.docker.com/products/docker-desktop |
| **Make** | Ejecutar los comandos del proyecto | Viene incluido en Linux/Mac. En Windows: instalar con WSL |

> **¿Estás en Windows?**
> Instala WSL (Windows Subsystem for Linux) y trabaja desde ahí.
> Abre PowerShell como administrador y ejecuta: `wsl --install`
> Luego abre la terminal de Ubuntu que aparece en el menú inicio.

Verifica que todo esté instalado correctamente:

```bash
git --version
docker --version
docker compose version
make --version
```

Si alguno de esos comandos falla, instálalo antes de continuar.

---

### Paso 2 — Clonar el repositorio

Descarga el código del proyecto en tu máquina:

```bash
git clone https://github.com/nicolasgarciae/proyecto1corte.git
cd proyecto1corte
```

Ahora estás dentro de la carpeta del proyecto. **Todos los comandos siguientes se ejecutan desde esta carpeta.**

---

### Paso 3 — Crear el archivo de configuración

El proyecto necesita un archivo `.env` con las contraseñas de la base de datos. Crea uno automáticamente con:

```bash
make setup
```

Verás este mensaje:

```
Archivo .env creado. Edita las contraseñas antes de continuar.
```

Abre el archivo `.env` que se acaba de crear:

```bash
nano .env
```

Verás algo así:

```env
MYSQL_ROOT_PASSWORD=cambia_esta_contrasena
MYSQL_USER=api_user
MYSQL_PASSWORD=cambia_esta_contrasena
MYSQL_DB=transporte_db
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_contrasena_de_aplicacion
SMTP_FROM=tu_correo@gmail.com
SMTP_FROM_NAME=ReservaYa
```

**Cambia los valores de `MYSQL_ROOT_PASSWORD` y `MYSQL_PASSWORD`** por contraseñas seguras de tu elección. Las otras variables de MySQL/RabbitMQ puedes dejarlas igual.

Las variables `SMTP_*` son para el envío de correos (factura de reserva). Si dejas `SMTP_HOST` vacío, el sistema funciona normal pero **no envía correos**. Para activarlos, ve a la sección [Configurar correos](#configurar-correos-opcional).

Guarda con `Ctrl+O`, luego `Enter`, luego `Ctrl+X`.

> **¿Por qué no subimos el `.env` al repo?**
> Porque contiene contraseñas. El archivo `.env` está en `.gitignore` para que nunca se suba accidentalmente a GitHub.

---

### Paso 4 — Iniciar Docker

Asegúrate de que Docker esté corriendo.

- **En Mac/Windows:** Abre Docker Desktop y espera a que el ícono de la ballena deje de moverse.
- **En Linux/WSL:** Ejecuta `sudo service docker start` o `sudo dockerd &`

Verifica que Docker responde:

```bash
docker info
```

Si ves información del sistema, Docker está listo.

---

### Paso 5 — Elegir cómo desplegar

Hay dos opciones. Elige la que aplique a tu caso:

---

#### Opción A — Despliegue desde DockerHub *(recomendado para producción)*

Usa la imagen ya construida y publicada en DockerHub. No necesitas el código fuente para compilar nada.

```bash
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1 deploy
```

Esto hace tres cosas automáticamente:
1. Verifica que `.env` existe
2. Descarga la imagen desde DockerHub
3. Levanta todos los contenedores

---

#### Opción B — Construir desde el código *(para desarrollo)*

Compila la imagen localmente desde el código que clonaste:

```bash
make up
```

Esto puede tardar unos minutos la primera vez porque descarga todas las imágenes base.

---

### Paso 6 — Esperar a que todo esté listo

Docker levanta los servicios en orden. MySQL tarda un poco en inicializarse. Puedes ver el estado con:

```bash
make status
```

Espera hasta que todos los servicios digan `Up` o `healthy`:

```
NAME                         STATUS
proyecto1corte-mysql         Up (healthy)
proyecto1corte-redis         Up (healthy)
proyecto1corte-rabbitmq      Up (healthy)
proyecto1corte-app           Up
proyecto1corte-worker        Up
proyecto1corte-redis-commander  Up
proyecto1corte-dozzle        Up
proyecto1corte-portainer     Up
```

Si alguno dice `starting`, espera 30 segundos y vuelve a correr `make status`.

---

### Paso 7 — Verificar que funciona

Haz una prueba rápida al endpoint de salud:

```bash
curl http://localhost:8014/health
```

Respuesta esperada:

```json
{"status": "ok"}
```

Si ves eso, el sistema está funcionando correctamente.

---

### Paso 8 — Abrir la aplicación

Abre tu navegador y entra a las siguientes direcciones:

| Panel | URL | Descripción |
|---|---|---|
| **Aplicación web** | http://localhost:8014 | Reservas y panel principal |
| **RabbitMQ** | http://localhost:15673 | Cola de mensajes |
| **Redis Commander** | http://localhost:8082 | Visor de caché y sesiones |
| **Dozzle** | http://localhost:8083 | Logs de contenedores en tiempo real |
| **Portainer** | https://localhost:9443 | Administración de Docker |

> **Portainer** puede mostrar una advertencia de seguridad porque usa HTTPS con certificado autofirmado. Haz clic en "Avanzado" → "Continuar de todas formas".
> La **primera vez** que abras Portainer te pedirá crear un usuario administrador.

**Credenciales del sistema:**

| Servicio | Usuario | Contraseña |
|---|---|---|
| App (admin) | `admin` | `admin` |
| RabbitMQ | `guest` | `guest` (o la que pusiste en `.env`) |

---

### Paso 9 — Apagar el sistema

Para detener todos los contenedores sin perder datos:

```bash
make down
```

Para detener **y borrar todos los datos** (base de datos incluida):

```bash
docker compose down -v
```

> ⚠️ Usa `down -v` solo si quieres empezar desde cero. Borra la base de datos MySQL permanentemente.

---

## Comandos útiles del día a día

```bash
make up          # Levantar el sistema
make down        # Apagar el sistema
make restart     # Reiniciar (reconstruye la imagen)
make logs        # Ver logs en tiempo real (Ctrl+C para salir)
make status      # Ver estado de los contenedores
make ps          # Ver todos los contenedores Docker activos
```

---

## Publicar una nueva versión en DockerHub

Si hiciste cambios en el código y quieres publicarlos:

```bash
# 1. Inicia sesión en DockerHub (solo la primera vez)
make login

# 2. Construye y sube la imagen con la nueva versión
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v2 push
```

Luego, en la otra máquina, actualiza con:

```bash
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v2 deploy
```

---

## Estructura del sistema

El `docker-compose.yml` levanta estos 8 servicios automáticamente:

```
proyecto1corte-app            → API FastAPI        → puerto 8014
proyecto1corte-worker         → Consumer RabbitMQ  → (sin puerto externo)
proyecto1corte-mysql          → Base de datos       → puerto 3307
proyecto1corte-redis          → Caché y sesiones    → puerto 6380
proyecto1corte-rabbitmq       → Cola de mensajes    → puertos 5673 / 15673
proyecto1corte-redis-commander → Panel Redis        → puerto 8082
proyecto1corte-dozzle         → Visor de logs       → puerto 8083
proyecto1corte-portainer      → Admin Docker        → puerto 9443
```

Los servicios se comunican entre sí por la red interna de Docker usando nombres (`mysql`, `redis`, `rabbitmq`). No necesitan IPs.

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Interfaz web |
| `GET` | `/health` | Estado de la API |
| `POST` | `/auth/register` | Crear cuenta (pide correo electrónico) |
| `POST` | `/auth/login` | Iniciar sesión |
| `GET` | `/auth/me` | Validar sesión activa |
| `POST` | `/auth/logout` | Cerrar sesión |
| `GET` | `/rutas` | Listar rutas disponibles |
| `GET` | `/rutas/{id}/disponibilidad` | Asientos libres por fecha |
| `POST` | `/reservas` | Crear reserva (envía factura por correo) |
| `GET` | `/reservas/mias` | Reservas del usuario actual |
| `GET` | `/admin/dashboard` | Panel administrador |
| `GET` | `/infra/status` | Estado de MySQL, Redis y RabbitMQ |

---

## Configurar correos (opcional)

Cuando un usuario hace una reserva, el sistema le envía la factura por correo. Para activarlo necesitas una cuenta de Gmail con **contraseña de aplicación**.

### Paso 1 — Generar la contraseña de aplicación

1. Entra a tu cuenta Google → activa la **verificación en 2 pasos**
2. Ve a https://myaccount.google.com/apppasswords
3. Crea una contraseña de aplicación → copia los 16 caracteres

> ⚠️ Es la **contraseña de aplicación** (16 caracteres), NO la contraseña normal de tu correo.

### Paso 2 — Editar el `.env`

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=tu_correo@gmail.com
SMTP_FROM_NAME=ReservaYa
```

### Paso 3 — Reconstruir

```bash
docker compose down
make up
```

### Verificar

Registra un usuario con correo real, haz una reserva y revisa la bandeja (y spam). Si no llega, mira los logs del worker:

```bash
docker logs proyecto1corte-worker --tail 30
```

Busca `Correo de reserva enviado` (éxito) o `Fallo el envio de correo` (error con detalle).

---

## Solución de problemas

### "No existe el archivo .env"

```bash
make setup
```

---

### Docker no responde o no está activo

En WSL / Linux:

```bash
sudo service docker start
```

Si tampoco funciona:

```bash
sudo dockerd &
```

Espera 10 segundos y vuelve a intentar.

---

### "pull access denied" o "image not found"

Significa que Docker no encontró la imagen. Si usas `make up`, construye primero:

```bash
make up
```

Si usas `make deploy`, verifica que `DOCKER_USERNAME` e `IMAGE_TAG` sean correctos:

```bash
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1 deploy
```

---

### Un puerto ya está en uso

Si ves `address already in use`, algún puerto está ocupado por otro proceso. Verifica cuál:

```bash
# Ver qué proceso usa el puerto 8014
sudo lsof -i :8014
```

O cambia el puerto en `docker-compose.yml` si no puedes liberar el que está ocupado.

---

### MySQL no arranca o dice "unhealthy"

Espera 30-60 segundos, MySQL tarda en inicializarse la primera vez. Si sigue fallando:

```bash
docker logs proyecto1corte-mysql
```

Lee el error. Si el volumen tiene datos corruptos de un intento anterior:

```bash
docker compose down -v
make setup
make up
```

---

### Reiniciar desde cero completamente

```bash
docker compose down -v    # Borra contenedores y volúmenes
make setup                # Recrea .env
make up                   # Levanta todo de nuevo
```

---

## Flujo de trabajo con Git

```bash
# Antes de empezar a trabajar
git checkout main
git pull origin main

# Crear rama para el cambio
git checkout -b feature-nombre-del-cambio

# Después de hacer los cambios
git add .
git commit -m "Descripcion clara del cambio"
git push -u origin feature-nombre-del-cambio
```

Luego abre un Pull Request en GitHub hacia `main`, revisa los cambios con tu equipo y haz merge.
