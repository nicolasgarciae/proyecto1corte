# ReservaYa

Sistema de reservas de buses intermunicipales. API en FastAPI, datos en MySQL, sesiones y caché en Redis, eventos por RabbitMQ y un worker que manda las facturas por correo. Todo levanta con Docker, así que no tienes que instalar Python ni bases de datos a mano.

Si solo quieres verlo corriendo, salta a [Levantarlo](#levantarlo).

## Qué necesitas

Git y Docker. Nada más.

```bash
git --version
docker --version
docker compose version
```

Si estás en Windows, todo esto va dentro de WSL. Si no lo tienes, abre PowerShell como admin y corre `wsl --install`, luego trabaja desde la terminal de Ubuntu. `make` viene de fábrica en Linux y Mac; en Windows lo tienes apenas instalas WSL.

## Levantarlo

Clona el repo y métete a la carpeta:

```bash
git clone https://github.com/nicolasgarciae/proyecto1corte.git
cd proyecto1corte
```

Antes de arrancar necesitas un `.env` con las contraseñas. Hay un comando que lo crea a partir de la plantilla:

```bash
make setup
nano .env
```

Cambia al menos `MYSQL_ROOT_PASSWORD` y `MYSQL_PASSWORD` por algo tuyo. El resto puedes dejarlo como está. Las variables `SMTP_*` solo importan si quieres que se manden correos; mientras `SMTP_HOST` esté vacío, el sistema corre igual pero no envía nada (mira [Correos](#correos) cuando quieras activarlos).

El `.env` no se sube al repo a propósito —tiene contraseñas y está en el `.gitignore`.

Con eso listo, levanta todo:

```bash
make up
```

La primera vez tarda un par de minutos bajando imágenes. Cuando termine, revisa que esté todo arriba:

```bash
make status
```

MySQL es el que más tarda en quedar `healthy`. Si ves algo en `starting`, dale 30 segundos y vuelve a mirar. Una prueba rápida de que la API responde:

```bash
curl http://localhost:8014/health
# {"status": "ok"}
```

La app queda en `http://localhost:8014`. El admin por defecto es `admin` / `admin`.

### Desplegar desde una imagen ya publicada

Si no quieres compilar y la imagen ya está en DockerHub, en vez de `make up`:

```bash
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v1 deploy
```

Eso baja la imagen y levanta los contenedores sin construir nada local. Útil para un servidor donde solo quieres correr, no desarrollar.

## Dónde queda cada cosa

| Servicio | Para qué | URL |
|---|---|---|
| App | La aplicación y la API | http://localhost:8014 |
| RabbitMQ | Cola de mensajes | http://localhost:15673 |
| Redis Commander | Ver caché y sesiones | http://localhost:8082 |
| Dozzle | Logs en vivo | http://localhost:8083 |
| Portainer | Administrar Docker | https://localhost:9443 |
| Duplicati | Backups de la base de datos | http://localhost:8200 |

Portainer usa HTTPS con certificado propio, así que el navegador se queja la primera vez —dale en "Avanzado" y continúa. También te pedirá crear un usuario admin al entrar.

Login del sistema: app con `admin` / `admin`, RabbitMQ con `guest` / `guest` (o lo que hayas puesto en el `.env`).

## Comandos del día a día

```bash
make up          # Levantar
make down        # Apagar
make restart     # Reiniciar reconstruyendo
make logs        # Logs en vivo (Ctrl+C para salir)
make status      # Estado de los contenedores
```

Para apagar sin perder datos basta `make down`. Si quieres borrar todo, base de datos incluida, es `docker compose down -v` —pero eso no tiene vuelta atrás, lo dejas como nuevo.

## Publicar una versión nueva

Cuando cambias código y quieres subir la imagen:

```bash
make login                                              # solo la primera vez
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v2 push
```

Y en la máquina donde corre, la actualizas con el mismo tag:

```bash
make DOCKER_USERNAME=nicolasgarciae1 IMAGE_TAG=v2 deploy
```

## Cómo está armado

El `docker-compose.yml` levanta diez contenedores:

```
app             API FastAPI                 8014
worker          consume eventos, manda correos   (interno)
mysql           base de datos               3307
redis           caché y sesiones            6380
rabbitmq        cola de eventos             5673 / 15673
redis-commander panel de Redis              8082
dozzle          logs en vivo                8083
portainer       admin de Docker             9443
db-backup       mysqldump periódico         (interno)
duplicati       backups cifrados            8200
```

Entre ellos se hablan por la red interna de Docker usando los nombres (`mysql`, `redis`, `rabbitmq`), así que no dependen de ninguna IP fija.

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/` | La interfaz web |
| `GET` | `/health` | Estado de la API |
| `POST` | `/auth/register` | Crear cuenta (pide correo) |
| `POST` | `/auth/login` | Entrar |
| `GET` | `/auth/me` | Validar sesión |
| `POST` | `/auth/logout` | Salir |
| `GET` | `/rutas` | Rutas disponibles |
| `GET` | `/rutas/{id}/disponibilidad` | Asientos libres por fecha |
| `POST` | `/reservas` | Reservar (dispara la factura por correo) |
| `GET` | `/reservas/mias` | Mis reservas |
| `GET` | `/admin/dashboard` | Panel del admin |
| `GET` | `/infra/status` | Si MySQL, Redis y RabbitMQ están vivos |

## Backups

La base de datos se respalda sola. Un contenedor (`db-backup`) le saca un `mysqldump` cada hora —con `--single-transaction`, que no bloquea la base mientras corre— y lo guarda en un volumen. Duplicati toma esos dumps y los respalda cifrados a donde quieras: una carpeta local, Google Drive, S3, lo que sea.

```
mysql → db-backup (dump cada hora) → volumen db_backups
                                          │ /source (solo lectura)
                                          ▼
                                     duplicati → cifra → destino
```

La razón de no respaldar directamente la carpeta de datos de MySQL es que copiarla en caliente da un backup roto: la base sigue escribiendo mientras se copia y luego no restaura. El dump evita eso porque es un snapshot consistente.

Para configurar Duplicati, entra a `http://localhost:8200` y crea un backup nuevo. En el origen apunta a `/source` (ahí caen los dumps) y en el destino a `/backups`, con una passphrase de cifrado que tienes que guardar —sin ella el backup no sirve de nada. Pones un horario y listo.

Para cambiar cada cuánto se hace el dump, en el `.env`:

```env
BACKUP_INTERVAL=3600   # segundos entre dumps
BACKUP_KEEP=24         # cuántos dumps conservar
```

Para confirmar que está corriendo:

```bash
docker logs proyecto1corte-db-backup --tail 5
```

Si algún día toca restaurar, Duplicati saca el `.sql` desde su interfaz y lo cargas con:

```bash
docker exec -i proyecto1corte-mysql mysql -uapi_user -pTU_PASSWORD transporte_db < dump.sql
```

## Correos

Al confirmar una reserva, el worker manda la factura al correo del usuario. Para que funcione necesitas una cuenta de Gmail con contraseña de aplicación (la de 16 caracteres, no la normal de tu cuenta).

La generas activando la verificación en dos pasos en tu cuenta de Google y luego en https://myaccount.google.com/apppasswords. Con eso, en el `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=tu_correo@gmail.com
SMTP_FROM_NAME=ReservaYa
```

Reconstruye para que el worker tome la config:

```bash
docker compose down
make up
```

Después regístrate con un correo real, haz una reserva y revisa la bandeja (y el spam). Si no llega, los logs del worker te dicen qué pasó:

```bash
docker logs proyecto1corte-worker --tail 30
```

Busca `Correo de reserva enviado` o, si falló, `Fallo el envio de correo` con el detalle.

## Cuando algo falla

**Dice que no existe el `.env`.** Corre `make setup`.

**Docker no responde.** En WSL o Linux, `sudo service docker start`. Si no, `sudo dockerd &` y espera unos segundos. En Mac o Windows, abre Docker Desktop y espera a que la ballena deje de moverse.

**`pull access denied` o no encuentra la imagen.** Docker intentó bajar una imagen que no existe. Si estás desarrollando, usa `make up` que la construye local. Si usas `deploy`, revisa que `DOCKER_USERNAME` e `IMAGE_TAG` sean los correctos.

**Un puerto está ocupado.** Si ves `address already in use`, mira quién lo tiene con `sudo lsof -i :8014` (cambia el número), o cambia el puerto en el `docker-compose.yml`.

**MySQL no arranca o queda `unhealthy`.** Casi siempre es que todavía está iniciando, dale un minuto. Si insiste, mira `docker logs proyecto1corte-mysql`. Si el volumen quedó con datos corruptos de un intento anterior, lo más rápido es empezar de cero:

```bash
docker compose down -v
make setup
make up
```

Eso mismo sirve cuando quieres resetearlo todo.

## Git

```bash
git checkout main
git pull origin main
git checkout -b feature-lo-que-sea

# trabajas, y cuando termines
git add .
git commit -m "Qué cambiaste"
git push -u origin feature-lo-que-sea
```

Luego abres el Pull Request hacia `main`.
