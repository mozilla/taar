all:
	# PySpark only knows eggs, not wheels
	python setup.py bdist_egg

upload:
	twine upload dist/*

test:
	python setup.py test
	flake8 taar tests


