all:
	# PySpark only knows eggs, not wheels
	python setup.py sdist

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

test:
	python setup.py develop
	python setup.py test
	flake8 taar tests
	#
# Updating pip hashes is awful
freeze:
	bin/hashfreeze
