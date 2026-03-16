# 🚌 API Reservas de Transporte

API REST construida con **FastAPI** y **MySQL** para gestionar rutas y reservas de transporte.

---

## 📋 Requisitos

- Python 3.9+
- MySQL 8.0+
- pip

---

## ⚙️ Instalación

```bash
# Clonar el repositorio
git clone <https://github.com/nicolasgarciae/proyecto1corte>
cd <proyecto1corte>

# Instalar dependencias
pip install fastapi uvicorn aiomysql
```

---

## 🗄️ Configuración de Base de Datos

Crea la base de datos y las tablas en MySQL:

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

La configuración de conexión se encuentra en `database.py`:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "api_user",
    "password": "123456",
    "db": "transporte_db"
}
```

---

## 🚀 Ejecutar el servidor

```bash
# Local (solo localhost)
uvicorn main:app --reload

# Red local (accesible desde otros dispositivos en la misma red)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en:
- Local: `http://localhost:8000`
- Red: `http://<172.20.87.41>:8000`

Documentación interactiva (Swagger): `http://localhost:8000/docs`

---

## 📡 Endpoints

### Rutas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/rutas` | Crear una nueva ruta |
| `GET`  | `/rutas` | Obtener todas las rutas |

#### POST `/rutas` — Crear ruta

**Body:**
```json
{
  "origen": "Pereira",
  "destino": "Bogotá",
  "capacidad": 40
}
```

**Respuesta:**
```json
{
  "mensaje": "Ruta creada",
  "id": "uuid-generado"
}
```

---

#### GET `/rutas` — Listar rutas

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "origen": "Pereira",
    "destino": "Bogotá",
    "capacidad": 40
  }
]
```

---

### Reservas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/reservas` | Crear una nueva reserva |
| `GET`  | `/reservas` | Obtener todas las reservas |

#### POST `/reservas` — Crear reserva

**Body:**
```json
{
  "nombre_pasajero": "Juan Pérez",
  "ruta_id": "uuid-de-la-ruta"
}
```

**Respuesta:**
```json
{
  "mensaje": "Reserva creada",
  "id": "uuid-generado"
}
```

> ⚠️ Retorna `404` si la `ruta_id` no existe.

---

#### GET `/reservas` — Listar reservas

**Respuesta:**
```json
[
  {
    "id": "uuid",
    "nombre_pasajero": "Juan Pérez",
    "origen": "Pereira",
    "destino": "Bogotá"
  }
]
```

---

## 📁 Estructura del proyecto

```
├── main.py          # Endpoints de la API
├── database.py      # Configuración y conexión a MySQL
└── README.md
```

---

## 🔥 Firewall (Windows)

Si vas a acceder desde otro dispositivo en la red, abre el puerto en CMD como administrador:

```cmd
netsh advfirewall firewall add rule name="FastAPI 8000" dir=in action=allow protocol=TCP localport=8000
```