import asyncio
import json
from datetime import datetime, timezone

import aio_pika
import redis.asyncio as redis

from database import RABBITMQ_QUEUE, RABBITMQ_URL, REDIS_URL

ADMIN_EVENT_KEY = "admin:eventos"
ADMIN_EVENT_LIMIT = 40


async def main():
    redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    rabbit_connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await rabbit_connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    print(f"Escuchando eventos en la cola '{RABBITMQ_QUEUE}'")

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                payload = json.loads(message.body.decode("utf-8"))
                payload["procesado_en"] = datetime.now(timezone.utc).isoformat()
                await redis_client.lpush(ADMIN_EVENT_KEY, json.dumps(payload))
                await redis_client.ltrim(ADMIN_EVENT_KEY, 0, ADMIN_EVENT_LIMIT - 1)
                print(f"Evento procesado: {payload['type']}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Consumer detenido")
