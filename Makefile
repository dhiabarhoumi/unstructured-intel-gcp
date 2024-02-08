.PHONY: all test lint format clean gcs-bootstrap help

# Default target
all: test lint

help:
	@echo "Available targets:"
	@echo "  all              - Run tests and linting"
	@echo "  test             - Run pytest with coverage"
	@echo "  lint             - Run ruff and mypy"
	@echo "  format           - Format code with black and ruff"
	@echo "  clean            - Remove cache and artifacts"
	@echo "  gcs-bootstrap    - Create GCS bucket structure"
	@echo "  docker-build     - Build Docker image"
	@echo "  docker-run       - Run Docker container locally"

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -x

test-unit:
	pytest tests/ -v -m "not integration"

lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports
	black --check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache

gcs-bootstrap:
	@echo "Creating GCS bucket structure..."
	gsutil mb -p $(PROJECT_ID) -l $(REGION) $(BUCKET) || true
	gsutil -m mkdir $(BUCKET)/bronze $(BUCKET)/silver $(BUCKET)/gold
	gsutil -m mkdir $(BUCKET)/reports $(BUCKET)/faiss
	@echo "GCS structure created successfully"

docker-build:
	docker build -t unstructured-intel-gcp:latest .

docker-run:
	docker run -p 8080:8080 \
		-e PROJECT_ID=$(PROJECT_ID) \
		-e FAISS_URI=$(BUCKET)/faiss/ \
		unstructured-intel-gcp:latest
