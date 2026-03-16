import aiomysql

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "api_user",
    "password": "123456",
    "db": "transporte_db"
}

async def get_connection():
    return await aiomysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        db=DB_CONFIG["db"]
    )