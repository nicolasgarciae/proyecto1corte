import asyncio
import json
import uuid
from datetime import datetime, timezone

import aio_pika
import redis.asyncio as redis

from database import RABBITMQ_QUEUE, RABBITMQ_URL, REDIS_URL
from logging_config import configure_logging

ADMIN_EVENT_KEY = "admin:eventos"
ADMIN_EVENT_LIMIT = 40

logger = configure_logging("consumer")


async def main():
    redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    rabbit_connection = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await rabbit_connection.channel()
    queue = await channel.declare_queue(RABBITMQ_QUEUE, durable=True)

    logger.info("Escuchando eventos", extra={"extra_fields": {"queue": RABBITMQ_QUEUE}})

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                payload = json.loads(message.body.decode("utf-8"))
                payload.setdefault("log_id", str(uuid.uuid4()))
                payload["procesado_en"] = datetime.now(timezone.utc).isoformat()
                await redis_client.lpush(ADMIN_EVENT_KEY, json.dumps(payload))
                await redis_client.ltrim(ADMIN_EVENT_KEY, 0, ADMIN_EVENT_LIMIT - 1)
                logger.info(
                    "Evento procesado",
                    extra={
                        "log_id": payload["log_id"],
                        "extra_fields": {"event_type": payload.get("type"), "queue": RABBITMQ_QUEUE},
                    },
                )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer detenido")
