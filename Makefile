VERSION := 0.0.1
BE_IMAGE_NAME := aimath-tutor-streamlit-fastapi_fast_api_backend_1
DOCKER_COMPOSE_FILE  := docker-compose-dev.yml 
FE_IMAGE_NAME := aimath-tutor-streamlit-fastapi_streamlit_frontend_1
BACKUP_DATE := $(shell date +%m_%d_%y)

up: 
	docker-compose -f $(DOCKER_COMPOSE_FILE)  up -d --build

stop-be:
	docker stop ${BE_IMAGE_NAME}
	docker rm ${BE_IMAGE_NAME}

stop-fe:
	docker stop ${FE_IMAGE_NAME}
	docker rm ${FE_IMAGE_NAME}

logs:
	docker-compose -f $(DOCKER_COMPOSE_FILE) logs -f --tail 15 

logs-be:
	docker logs $(BE_IMAGE_NAME) -f --tail 150 

logs-fe: 
	docker logs $(FE_IMAGE_NAME) -f --tail 150
