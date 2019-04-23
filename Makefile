.PHONY: build up tests flake8 ci tests-with-cov

all:
	# PySpark only knows eggs, not wheels
	python setup.py sdist

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

pytest:
	python setup.py develop
	python setup.py test
	flake8 taar tests

build:
	docker-compose build

up:
	docker-compose up

testsnocov:
	docker-compose run web tox -etestsnocov

tests:
	docker-compose run web tox -etests

flake8:
	docker-compose run web tox -eflake8

ci:
	docker-compose run web tox

shell:
	docker-compose run web bash 
