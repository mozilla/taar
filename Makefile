.PHONY: build up tests flake8 ci tests-with-cov

all:
	# PySpark only knows eggs, not wheels
	python setup.py sdist

setup_conda:
	# Install all dependencies and setup repo in dev mode
	conda env update -n taar-37 -f enviroment.yml
	python setup.py develop

upload:
	twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

pytest:
	python setup.py develop
	python setup.py test
	flake8 taar tests

build:
	docker build . -t taar:latest

up:
	docker run \
		--rm \
		--name=taar \
		-v ~/.config:/app/.config \
		-v ~/.aws:/app/.aws \
		-v ~/.gcp_creds:/app/.gcp_creds \
		-e WORKERS=1 \
		-e THREADS=2 \
		-e LOG_LEVEL=20 \
		-e GOOGLE_APPLICATION_CREDENTIALS=/app/.gcp_creds/vng-taar-dev-clientinfo-svc.json \
		-e TAAR_API_PLUGIN=taar.plugin \
		-e TAAR_ITEM_MATRIX_BUCKET=telemetry-public-analysis-2 \
		-e TAAR_ITEM_MATRIX_KEY=telemetry-ml/addon_recommender/item_matrix.json \
		-e TAAR_ADDON_MAPPING_BUCKET=telemetry-public-analysis-2 \
		-e TAAR_ADDON_MAPPING_KEY=telemetry-ml/addon_recommender/addon_mapping.json \
		-e TAAR_ENSEMBLE_BUCKET=telemetry-parquet \
		-e TAAR_ENSEMBLE_KEY=taar/ensemble/ensemble_weight.json \
		-e TAAR_WHITELIST_BUCKET=telemetry-parquet \
		-e TAAR_WHITELIST_KEY=telemetry-ml/addon_recommender/only_guids_top_200.json \
		-e TAAR_LOCALE_BUCKET=telemetry-parquet \
		-e TAAR_LOCALE_KEY=taar/locale/top10_dict.json \
		-e TAAR_SIMILARITY_BUCKET=telemetry-parquet \
		-e TAAR_SIMILARITY_DONOR_KEY=taar/similarity/donors.json \
		-e TAAR_SIMILARITY_LRCURVES_KEY=taar/similarity/lr_curves.json \
		-e TAAR_MAX_RESULTS=10 \
		-e TAARLITE_MAX_RESULTS=4 \
		-e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
		-e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		-e BIGTABLE_PROJECT_ID=${BIGTABLE_PROJECT_ID} \
		-e BIGTABLE_INSTANCE_ID=${BIGTABLE_INSTANCE_ID} \
		-e BIGTABLE_TABLE_ID=${BIGTABLE_TABLE_ID} \
		-e GCLOUD_PROJECT=${GCLOUD_PROJECT} \
		-p 8000:8000 \
		-it taar:latest 

test-container:
	docker run -e CODECOV_TOKEN=${CODECOV_TOKEN} -it taar:latest test

run_local:
	TAAR_API_PLUGIN=taar.plugin python taar/flask_app.py

shell:
	docker run -it taar:latest bash 
