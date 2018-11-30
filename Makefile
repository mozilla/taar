.PHONY: build up tests flake8 ci

all:
	# PySpark only knows eggs, not wheels
	python setup.py sdist

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

test:
	python setup.py develop
	python setup.py test
	flake8 taar tests

build:
	docker-compose build

up:
	docker-compose up

tests:
	docker-compose run web tox -etests

flake8:
	docker-compose run web tox -eflake8

ci:
	docker-compose run web tox

shell:
	docker-compose run web bash 
