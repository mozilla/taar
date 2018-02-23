all:
	# PySpark only knows eggs, not wheels
	python setup.py bdist_egg

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

test:
	python setup.py test
	flake8 taar tests


