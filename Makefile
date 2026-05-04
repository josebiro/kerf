.PHONY: dev-backend dev-frontend

DOCKER_IMAGE_NAME=kerf
DOCKER_REGISTRY=josebiro


##@ Utility
help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

clean: ## Tidy up local environment
	find . -name \*.pyc -delete
	find . -name __pycache__ -delete

dev-backend: ## Start the development backend server
	 cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Start the developmentfrontend server
	cd frontend && npm run dev

docker-build: ## Build the Docker image for the application
	docker build -t ${DOCKER_IMAGE_NAME} .

docker-run: ## Run the Docker container for the application
	docker run -p 8000:8000 ${DOCKER_IMAGE_NAME}

docker-publish: ## Publish the Docker image to a registry
	docker tag ${DOCKER_IMAGE_NAME} ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest
	docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:latest	