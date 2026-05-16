.DEFAULT_GOAL := help

PROJECT_NAME ?= proyecto1corte
DOCKER_USERNAME ?= usuario
IMAGE_TAG ?= v1
DOCKER_IMAGE ?= $(DOCKER_USERNAME)/$(PROJECT_NAME)-api:$(IMAGE_TAG)

.PHONY: help up down logs restart ps start portainer status build image images login tag push pull deploy github-flow

help:
	@echo "Comandos disponibles:"
	@echo "  make github-flow  Muestra el flujo de ramas recomendado"
	@echo "  make up           Levanta los contenedores y reconstruye imagenes"
	@echo "  make down         Detiene y elimina los contenedores"
	@echo "  make logs         Muestra logs en tiempo real"
	@echo "  make restart      Reinicia los contenedores reconstruyendo imagenes"
	@echo "  make ps           Lista contenedores activos de Docker"
	@echo "  make status       Muestra el estado de Docker Compose"
	@echo "  make start        Ejecuta el arranque completo del proyecto en WSL"
	@echo "  make portainer    Levanta solo Portainer"
	@echo "  make build        Construye la imagen local"
	@echo "  make login        Inicia sesion en DockerHub"
	@echo "  make push         Publica la imagen en DockerHub"
	@echo "  make pull         Descarga la imagen desde DockerHub"
	@echo "  make deploy       Descarga imagen y levanta el sistema"
	@echo ""
	@echo "Variables:"
	@echo "  DOCKER_USERNAME=$(DOCKER_USERNAME)"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  DOCKER_IMAGE=$(DOCKER_IMAGE)"

github-flow:
	@echo "GitHub Flow recomendado:"
	@echo "  1. git checkout main && git pull origin main"
	@echo "  2. git checkout -b feature-nombre"
	@echo "  3. git add . && git commit -m 'Descripcion del cambio'"
	@echo "  4. git push -u origin feature-nombre"
	@echo "  5. Abrir Pull Request hacia main"
	@echo "  6. Revisar, aprobar y hacer merge"

up:
	DOCKER_IMAGE=proyecto1corte-api:local docker compose build app
	DOCKER_IMAGE=proyecto1corte-api:local docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down
	DOCKER_IMAGE=proyecto1corte-api:local docker compose build app
	DOCKER_IMAGE=proyecto1corte-api:local docker compose up -d

ps:
	docker ps

start:
	sudo ./start_all.sh

portainer:
	docker compose up -d portainer

status:
	docker compose ps

build image:
	docker build -t $(DOCKER_IMAGE) .

images:
	docker images | grep $(PROJECT_NAME) || true

login:
	docker login

tag:
	docker tag $(DOCKER_IMAGE) $(DOCKER_USERNAME)/$(PROJECT_NAME)-api:latest

push: build
	docker push $(DOCKER_IMAGE)

pull:
	docker pull $(DOCKER_IMAGE)

deploy: pull
	DOCKER_IMAGE=$(DOCKER_IMAGE) docker compose up -d
