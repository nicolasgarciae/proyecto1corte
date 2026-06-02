.DEFAULT_GOAL := help

export BUILDX_NO_DEFAULT_ATTESTATIONS=1
export DOCKER_BUILDKIT=0

PROJECT_NAME    ?= proyecto1corte
DOCKER_USERNAME ?= usuario
IMAGE_TAG       ?= v1
LOCAL_IMAGE     := $(PROJECT_NAME)-api:local
DOCKER_IMAGE    ?= $(DOCKER_USERNAME)/$(PROJECT_NAME)-api:$(IMAGE_TAG)

.PHONY: help up down logs restart ps start portainer status build images login tag push pull deploy github-flow setup _check_user _check_env

help:
	@echo ""
	@echo "  Uso: make [target] [DOCKER_USERNAME=tu_usuario] [IMAGE_TAG=v2]"
	@echo ""
	@echo "  Primera vez en una maquina nueva:"
	@echo "    make setup        Crea .env a partir de .env.example"
	@echo ""
	@echo "  Desarrollo local:"
	@echo "    make up           Construye imagen local y levanta contenedores"
	@echo "    make down         Detiene y elimina los contenedores"
	@echo "    make restart      Reinicia reconstruyendo la imagen"
	@echo "    make logs         Muestra logs en tiempo real"
	@echo "    make ps           Lista contenedores activos"
	@echo "    make status       Estado de Docker Compose"
	@echo "    make portainer    Levanta solo Portainer"
	@echo "    make start        Arranque completo en WSL (script local)"
	@echo ""
	@echo "  DockerHub (requiere DOCKER_USERNAME):"
	@echo "    make build        Construye imagen etiquetada para DockerHub"
	@echo "    make images       Lista imagenes del proyecto"
	@echo "    make login        Inicia sesion en DockerHub"
	@echo "    make push         Construye y publica la imagen"
	@echo "    make pull         Descarga la imagen desde DockerHub"
	@echo "    make tag          Etiqueta imagen como :latest"
	@echo "    make deploy       Descarga imagen y levanta el sistema"
	@echo ""
	@echo "  Variables actuales:"
	@echo "    DOCKER_USERNAME = $(DOCKER_USERNAME)"
	@echo "    IMAGE_TAG       = $(IMAGE_TAG)"
	@echo "    LOCAL_IMAGE     = $(LOCAL_IMAGE)"
	@echo "    DOCKER_IMAGE    = $(DOCKER_IMAGE)"
	@echo ""

github-flow:
	@echo ""
	@echo "  GitHub Flow recomendado:"
	@echo "    1. git checkout main && git pull origin main"
	@echo "    2. git checkout -b feature-nombre"
	@echo "    3. git add . && git commit -m 'Descripcion del cambio'"
	@echo "    4. git push -u origin feature-nombre"
	@echo "    5. Abrir Pull Request hacia main"
	@echo "    6. Revisar, aprobar y hacer merge"
	@echo ""

# Guard: falla si DOCKER_USERNAME no fue sobreescrito
_check_user:
	@python3 -c "import sys; sys.exit('\nERROR: DOCKER_USERNAME sigue siendo el valor por defecto.\nUso: make DOCKER_USERNAME=tunombre <target>\n') if '$(DOCKER_USERNAME)'=='usuario' else None"

# Guard: falla si .env no existe
_check_env:
	@python3 -c "import os,sys; sys.exit('\nERROR: No existe .env.\nEjecuta primero: make setup\n') if not os.path.exists('.env') else None"

# ── Primera vez ───────────────────────────────────────────────────────────────

setup:
	@python3 -c "import shutil,os; \
		print('.env ya existe, no se sobreescribe.') if os.path.exists('.env') \
		else (shutil.copy('.env.example','.env'), print('Archivo .env creado. Edita las contrasenas antes de continuar.'))"

# ── Desarrollo local ──────────────────────────────────────────────────────────

up: _check_env
	docker build --provenance=false -t $(LOCAL_IMAGE) .
	DOCKER_IMAGE=$(LOCAL_IMAGE) docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart: down up

ps:
	docker ps

status:
	docker compose ps

portainer:
	docker compose up -d portainer

start:
	chmod +x ./start_all.sh
	sudo bash ./start_all.sh

# ── DockerHub ─────────────────────────────────────────────────────────────────

build: _check_user
	docker build --provenance=false -t $(DOCKER_IMAGE) .

images:
	docker images | grep $(PROJECT_NAME) || true

login:
	docker login

tag: _check_user
	docker tag $(DOCKER_IMAGE) $(DOCKER_USERNAME)/$(PROJECT_NAME)-api:latest

push: build
	docker push $(DOCKER_IMAGE)

pull: _check_user
	docker pull $(DOCKER_IMAGE)

deploy: _check_env pull
	DOCKER_IMAGE=$(DOCKER_IMAGE) docker compose up -d
