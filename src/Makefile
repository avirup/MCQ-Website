    # Makefile for MCQ Platform
    # Usage examples:
    #   make setup
    #   make migrate
    #   make run
    #   make test

    PY?=python
    PIP?=pip
    FLASK?=flask
    VENV?=venv
    APP?=manage.py

    .PHONY: setup venv install env db-init migrate upgrade run test clean

    setup: venv install env

    venv:
	$(PY) -m venv $(VENV)

    install:
	$(VENV)/bin/$(PIP) install -r requirements.txt
	@echo "If on macOS/Linux: export FLASK_APP=$(APP) or use .flaskenv"

    env:
	@echo "Environment files present:"
	@ls -1 .env .flaskenv 2>/dev/null || true

    db-init:
	$(VENV)/bin/$(FLASK) db init || true

    migrate:
	$(VENV)/bin/$(FLASK) db migrate -m "auto"

    upgrade:
	$(VENV)/bin/$(FLASK) db upgrade

    run:
	$(VENV)/bin/$(FLASK) run

    test:
	$(VENV)/bin/$(PIP) install pytest
	$(VENV)/bin/pytest -q

    clean:
	rm -rf __pycache__ */__pycache__ *.pyc *.pyo .pytest_cache
