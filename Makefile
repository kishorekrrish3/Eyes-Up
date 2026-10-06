.PHONY: help install run test test-outside clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make run           - Launch Eyes Up app server"
	@echo "  make test          - Run test suite"
	@echo "  make clean         - Remove temporary and cache files"

install:
	pip install -r requirements.txt

run:
	python run.py

test:
	pytest -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
