.DEFAULT_GOAL := docker

.PHONY: help
help: ## show this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## create virtual environment and install all dependencies
	@echo "creating virtual environment using poetry"
	@poetry install
	@poetry run pre-commit install

.PHONY: check
check: ## run checks: lock file consistency, linting, and obsolete dependency check
	@echo "checking poetry lock file consistency with 'pyproject.toml': running poetry check --lock"
	@poetry check --lock
	@echo "linting code: running pre-commit"
	@poetry run pre-commit run -a
	@echo "checking for obsolete dependencies: running deptry"
	@poetry run deptry .

.PHONY: docker-build
docker-build: ## build the nutalert docker image
	docker build -t nutalert -f Dockerfile .

.PHONY: docker-run
docker-run: ## run the container named nutalert using the nutalert image
	docker run -p 3493:3493 -p 8089:8080 -v $(shell pwd):/config --name nutalert nutalert

.PHONY: docker
docker: clean docker-build docker-run

.PHONY: clean
clean: ## clean docker containers, volumes, Python cache, build artifacts and temporary files
	-docker rm -f nutalert 2>/dev/null || true
	-docker volume rm nutalert_data 2>/dev/null || true
	@echo "cleaning python cache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -name ".pytest_cache" -exec rm -rf {} +
	find . -name ".coverage" -delete
	find . -name "htmlcov" -exec rm -rf {} +
	@echo "cleaning build artifacts..."
	rm -rf dist/ build/
	@echo "cleaning log files..."
	find . -name "*.log" -delete
	@echo "clean complete"
