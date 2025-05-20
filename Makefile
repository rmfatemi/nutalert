.DEFAULT_GOAL := docker

.PHONY: help
help: ## Show this help message.
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Create virtual environment and install all dependencies.
	@echo "creating virtual environment using poetry"
	@poetry install
	@poetry run pre-commit install

.PHONY: check
check: ## Run checks: lock file consistency, linting, and obsolete dependency check.
	@echo "checking poetry lock file consistency with 'pyproject.toml': running poetry check --lock"
	@poetry check --lock
	@echo "linting code: running pre-commit"
	@poetry run pre-commit run -a
	@echo "checking for obsolete dependencies: running deptry"
	@poetry run deptry .

.PHONY: docker-build
docker-build: ## Build the nutalert Docker image.
	docker build -t nutalert -f Dockerfile .

.PHONY: docker-run
docker-run: ## Run the container named nutalert using the nutalert image.
	docker volume create nutalert_data && docker run -p 3493:3493 -v nutalert_data:/app/data --name nutalert nutalert

.PHONY: docker
docker: clean docker-build docker-run

.PHONY: clean
clean: ## Clean Docker containers, volumes, Python cache, build artifacts and temporary files.
	@echo "cleaning docker resources..."
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
