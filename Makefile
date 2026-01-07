# =============================================================================
# Autonomous Research Agent - Makefile
# =============================================================================
# Common commands for development, testing, and deployment
# =============================================================================

.PHONY: help install install-dev test lint format clean build docker-build docker-up docker-down docker-logs run dev

# Default target
help:
	@echo "Autonomous Research Agent - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Development:"
	@echo "  make install       Install production dependencies"
	@echo "  make install-dev   Install development dependencies"
	@echo "  make run           Run the Streamlit application"
	@echo "  make dev           Run in development mode with hot reload"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linting checks (ruff)"
	@echo "  make format        Format code (black + ruff)"
	@echo "  make type-check    Run type checking (mypy)"
	@echo "  make check         Run all checks (lint + type-check)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run tests"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make test-fast     Run tests without slow tests"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-up     Start containers (production)"
	@echo "  make docker-dev    Start containers (development)"
	@echo "  make docker-down   Stop containers"
	@echo "  make docker-logs   View container logs"
	@echo "  make docker-shell  Open shell in container"
	@echo ""
	@echo "Build & Release:"
	@echo "  make build         Build Python package"
	@echo "  make clean         Clean build artifacts"
	@echo ""

# =============================================================================
# Installation
# =============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install || true

# =============================================================================
# Running the Application
# =============================================================================

run:
	streamlit run streamlit_app.py --server.port=8501

dev:
	streamlit run streamlit_app.py --server.port=8501 --server.runOnSave=true

# =============================================================================
# Code Quality
# =============================================================================

lint:
	ruff check src/ tests/
	black --check src/ tests/

format:
	black src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/ --ignore-missing-imports

check: lint type-check

# =============================================================================
# Testing
# =============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/research_agent --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-fast:
	pytest tests/ -v -m "not slow"

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Application running at http://localhost:8501"

docker-dev:
	docker-compose --profile dev up research-agent-dev
	@echo "Development server running at http://localhost:8501"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec research-agent /bin/bash

docker-clean:
	docker-compose down -v --rmi local
	docker system prune -f

# =============================================================================
# Build & Release
# =============================================================================

build:
	pip install build
	python -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Utilities
# =============================================================================

config-check:
	python -c "from research_agent.config import settings; print('Config OK' if settings.is_valid else 'Config Invalid')"

version:
	@python -c "from research_agent import __version__; print(__version__)"
