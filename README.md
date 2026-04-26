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

- Redis en `localhost:6380`
- RabbitMQ AMQP en `localhost:5673`
- Panel de RabbitMQ en `http://localhost:15673`
- Redis Commander en `http://localhost:8082`

Credenciales del panel RabbitMQ:

- usuario: `guest`
- contrasena: `guest`

Redis Commander no necesita credenciales adicionales en esta configuracion y se conecta al contenedor `redis` del mismo `docker compose`.

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
