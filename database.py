import os

from dotenv import load_dotenv

import aiomysql

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "api_user"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "db": os.getenv("MYSQL_DB", "transporte_db"),
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "reservas_eventos")


async def get_connection():
    return await aiomysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        db=DB_CONFIG["db"],
        autocommit=False,
        charset="utf8mb4",
    )
