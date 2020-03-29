.DEFAULT: help
.PHONY: help tests

help:
	@echo Targets are: tests

clean:
	find . -name "*.pyc" -type f -delete
	find . -name "*.pkl" -type f -delete
	find . -name "__pycache__" -delete
	find . -name ".#*" -delete
	find . -name "#*#" -delete

# testing

tests: unittest 

unittest:
	@echo "Running standard unit tests.."
	python3 -m unittest discover -s tests -v -p "*_tests.py" || (echo "Error in standard unit tests."; exit 1)
	PYTHONPATH=. pytest -vvv
