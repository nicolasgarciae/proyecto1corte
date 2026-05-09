# API Reservas de Transporte

Proyecto de reservas de transporte con FastAPI, MySQL, Redis y RabbitMQ.

## Lo que incluye ahora

- Login y registro de usuarios.
- Sesiones con token usando Redis cuando esta disponible.
- Credenciales fijas del administrador:
  - Usuario: `admin`
  - Contrasena: `admin`
- Panel administrador protegido por backend y frontend.
- Usuarios normales pueden ver rutas e iniciar sesion para hacer reservas.
- Redis para cache y sesiones.
- RabbitMQ para publicar eventos operativos.
- `consumer.py` para procesar la cola y guardar actividad reciente en Redis.
- Dozzle para observar logs de contenedores Docker desde un panel web.
- Logs JSON con `log_id` UUID en la API y el consumer.
- Contenedor `proyecto1corte-app` que inicia la API y el consumer juntos.

## Requisitos

- Python 3.9+
- MySQL 8+
- Redis
- RabbitMQ
- pip

## Instalacion

```bash
pip install -r requirements.txt
```

## Variables de entorno

La aplicacion ahora lee automaticamente el archivo `.env` si existe.

Archivo recomendado:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=api_user
MYSQL_PASSWORD=123456
MYSQL_DB=transporte_db
REDIS_URL=redis://localhost:6380/0
RABBITMQ_URL=amqp://guest:guest@localhost:5673/
RABBITMQ_QUEUE=reservas_eventos
```

## Base de datos

La API crea la tabla `users` automaticamente al arrancar y si hace falta agrega la columna `user_id` a `reservas`.

Tablas base esperadas:

```sql
CREATE DATABASE transporte_db;

CREATE USER 'api_user'@'localhost' IDENTIFIED BY '123456';
GRANT ALL PRIVILEGES ON transporte_db.* TO 'api_user'@'localhost';
FLUSH PRIVILEGES;

USE transporte_db;

CREATE TABLE rutas (
    id VARCHAR(36) PRIMARY KEY,
    origen VARCHAR(100) NOT NULL,
    destino VARCHAR(100) NOT NULL,
    capacidad INT NOT NULL
);

CREATE TABLE reservas (
    id VARCHAR(36) PRIMARY KEY,
    nombre_pasajero VARCHAR(100) NOT NULL,
    ruta_id VARCHAR(36) NOT NULL,
    FOREIGN KEY (ruta_id) REFERENCES rutas(id)
);
```

## Redis y RabbitMQ con Docker

Se dejaron puertos alternos para evitar conflicto con servicios ya instalados fuera de Docker:

```bash
docker compose up -d
```

Servicios:

- App + consumer en `http://127.0.0.1:8014`
- Redis en `localhost:6380`
- RabbitMQ AMQP en `localhost:5673`
- Panel de RabbitMQ en `http://localhost:15673`
- Redis Commander en `http://localhost:8082`
- Dozzle en `http://localhost:8083`

Credenciales del panel RabbitMQ:

- usuario: `guest`
- contrasena: `guest`

Redis Commander no necesita credenciales adicionales en esta configuracion y se conecta al contenedor `redis` del mismo `docker compose`.

Dozzle se conecta al socket de Docker en modo lectura para mostrar los logs de los contenedores del proyecto.

Nota:

- Los paneles web de RabbitMQ y Redis Commander se exponen de forma estable cuando levantas el proyecto con `sudo ./start_all.sh`.
- Eso evita conflictos de puertos cuando vuelves a ejecutar el arranque.

## Ejecutar la API

```bash
uvicorn main:app --reload
```

Si el puerto `8000` esta ocupado:

```bash
uvicorn main:app --reload --port 8014
```

## Abrir la interfaz

- `http://localhost:8000/`
- o `http://localhost:8014/` si usaste otro puerto

## Observabilidad basica

Opcion A con Dozzle:

```bash
sudo ./start_all.sh
```

Luego abre `http://localhost:8083` para ver los logs de los contenedores. La API y el consumer corren juntos dentro de `proyecto1corte-app` y emiten logs JSON con un campo `log_id` UUID; los eventos publicados en RabbitMQ tambien guardan ese `log_id` para poder rastrearlos entre productor, cola, consumer y panel admin.

## Contenedor de aplicacion

El servicio `app` de Docker Compose construye la imagen local del proyecto y arranca dos procesos dentro del mismo contenedor:

```bash
uvicorn main:app --host 0.0.0.0 --port 8014
python consumer.py
```

El contenedor usa `network_mode: host` para conectarse a MariaDB en `localhost:3306` y a los puertos publicados de Redis y RabbitMQ.

## Ejecutar el consumer

En otra terminal:

```bash
python consumer.py
```

## Flujo de acceso

- `Sign in`: crea una cuenta nueva y abre sesion automaticamente.
- `Login`: entra con un usuario existente.
- `admin/admin`: desbloquea el panel de administrador.
- Usuarios normales: solo pueden ver rutas y reservar.

## Endpoints principales

- `GET /` interfaz web
- `POST /auth/register` crear cuenta
- `POST /auth/login` iniciar sesion
- `GET /auth/me` validar sesion
- `POST /auth/logout` cerrar sesion
- `GET /rutas` listar rutas con ocupacion
- `POST /reservas` crear reserva con sesion iniciada
- `GET /admin/dashboard` panel admin
- `GET /admin/eventos` eventos procesados
- `GET /infra/status` estado de MySQL, Redis y RabbitMQ
