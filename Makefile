.DEFAULT_GOAL := help

.PHONY: help up down logs restart ps start portainer status

help:
	@echo "Comandos disponibles:"
	@echo "  make up         Levanta los contenedores y reconstruye imagenes"
	@echo "  make down       Detiene y elimina los contenedores"
	@echo "  make logs       Muestra logs en tiempo real"
	@echo "  make restart    Reinicia los contenedores reconstruyendo imagenes"
	@echo "  make ps         Lista contenedores activos de Docker"
	@echo "  make start      Ejecuta el arranque completo del proyecto"
	@echo "  make portainer  Levanta solo Portainer"
	@echo "  make status     Muestra el estado de Docker Compose"


up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down
	docker compose up -d --build

ps:
	docker ps

start:
	sudo ./start_all.sh

portainer:
	docker compose up -d portainer

status:
	docker compose ps
