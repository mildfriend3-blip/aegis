.PHONY: help install test run report clean

help:            ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

install:         ## install in editable mode with dev extras
	pip install -e ".[dev]"

test:            ## run the test suite
	pytest -q

run:             ## run the full benchmark
	python -m aegis.cli run --out results

report:          ## rebuild the technical writeup PDF
	python docs/build_writeup.py

clean:           ## remove caches and generated output
	rm -rf .pytest_cache **/__pycache__ results/*.json
