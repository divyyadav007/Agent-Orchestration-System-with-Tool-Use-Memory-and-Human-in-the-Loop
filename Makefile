# Makefile - AOS Development commands and shortcuts

.PHONY: setup install test lint format run docker-up docker-down clean help

help:
	@echo "Available commands:"
	@echo "  make setup        - Set up virtual environment and install packages"
	@echo "  make install      - Install project dependencies"
	@echo "  make test         - Run all integration tests via module path"
	@echo "  make lint         - Run Flake8 and black checks"
	@echo "  make format       - Format code using Black and Isort"
	@echo "  make run          - Launch Streamlit dashboard local server"
	@echo "  make docker-up    - Build and launch AOS service containers"
	@echo "  make docker-down  - Stop all AOS Docker containers"
	@echo "  make clean        - Remove Python caches and checkpoints"

setup:
	python -m venv .venv
	@echo "Virtual environment created. Please activate it manually."

install:
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	python -m tests.test_graph
	python -m tests.test_tools
	python -m tests.test_supervisor
	python -m tests.test_research

lint:
	black --check src tests
	flake8 src tests

format:
	isort src tests
	black src tests

run:
	streamlit run frontend/review-ui/app.py

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

clean:
	rm -rf __pycache__ src/**/__pycache__ tests/__pycache__
	rm -rf .pytest_cache .venv
	rm -f agent_checkpoints.db