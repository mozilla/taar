.PHONY: build up tests flake8 ci tests-with-cov

all:
	# PySpark only knows eggs, not wheels
	python setup.py sdist

setup_conda:
	# Install all dependencies and setup repo in dev mode
	conda env update -n taar-37 -f environment.yml
	python setup.py develop

conda_update:
    # Actualize env after .yml file was modified
	conda env update -n taar-37 -f environment.yml --prune

conda_export:
	conda env export > environment.yml

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

pytest:
	python setup.py develop
	python setup.py test
	flake8 taar tests

build:
	docker build . -t taar:latest

up:
	docker-compose up

test-container:
	docker run -e CODECOV_TOKEN=${CODECOV_TOKEN} -it taar:latest test

run_local:
	. bin/test_env.sh && python taar/flask_app.py -H 0.0.0.0 -P 8001

run_package_test:
	python setup.py develop
	python bin/run_package_test.py

shell:
	docker run -it taar:latest bash 
