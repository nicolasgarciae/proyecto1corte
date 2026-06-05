import asyncio
import json
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage

import aio_pika
import aiosmtplib
import redis.asyncio as redis

from database import (
    RABBITMQ_QUEUE,
    RABBITMQ_URL,
    REDIS_URL,
    SMTP_FROM,
    SMTP_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from logging_config import configure_logging

ADMIN_EVENT_KEY = "admin:eventos"
ADMIN_EVENT_LIMIT = 40

logger = configure_logging("consumer")


def format_money(value) -> str:
    try:
        return "$ {:,.0f}".format(int(value)).replace(",", ".")
    except (TypeError, ValueError):
        return str(value)


def build_reservation_email(payload: dict) -> tuple[str, str]:
    reserva_id = payload.get("id", "")
    nombre = payload.get("nombre_pasajero", "")
    origen = payload.get("origen", "")
    destino = payload.get("destino", "")
    fecha = payload.get("fecha_reserva", "")
    asiento = payload.get("asiento", "")
    metodo = payload.get("metodo_pago", "")
    precio = format_money(payload.get("precio", 0))
    horario = "Manana" if payload.get("horario") == "manana" else "Tarde/Noche"

    subject = f"Confirmacion de reserva {origen} - {destino}"

    body = f"""Hola {nombre},

Tu reserva fue confirmada. Estos son los detalles:

  Codigo de reserva : {reserva_id}
  Ruta              : {origen} -> {destino}
  Fecha             : {fecha}
  Horario           : {horario}
  Asiento           : {asiento}
  Metodo de pago    : {metodo}
  Total pagado      : {precio}

Gracias por viajar con ReservaYa.
"""
    return subject, body


async def send_reservation_email(payload: dict) -> None:
    to_email = payload.get("email")
    if not to_email:
        logger.warning(
            "Reserva sin email, no se envia correo",
            extra={"extra_fields": {"reserva_id": payload.get("id")}},
        )
        return

    if not SMTP_HOST or not SMTP_USER:
        logger.warning(
            "SMTP no configurado, se omite envio de correo",
            extra={"extra_fields": {"reserva_id": payload.get("id")}},
        )
        return

    subject, body = build_reservation_email(payload)

    message = EmailMessage()
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=SMTP_PORT == 587,
            use_tls=SMTP_PORT == 465,
        )
        logger.info(
            "Correo de reserva enviado",
            extra={"extra_fields": {"reserva_id": payload.get("id"), "to": to_email}},
        )
    except Exception as exc:
        logger.error(
            "Fallo el envio de correo de reserva",
            extra={"extra_fields": {"reserva_id": payload.get("id"), "error": str(exc)}},
        )


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

                if payload.get("type") == "reserva_creada":
                    await send_reservation_email(payload.get("payload", {}))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer detenido")
