FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt \
    && pip install --quiet --upgrade pip

COPY . .
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8014

CMD ["/app/docker-entrypoint.sh"]
