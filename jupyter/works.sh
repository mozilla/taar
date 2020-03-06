#!/bin/bash

gcloud beta dataproc clusters create jupyter-ensemble-works \
    --bucket jupyter-ensemble \
    --enable-component-gateway \
    --image-version=1.4 \
    --initialization-actions gs://dataproc-initialization-actions/python/pip-install.sh \
    --max-idle 10m \
    --metadata "PIP_PACKAGES=mozilla-taar3==0.4.8 mozilla-srgutil==0.2.1 python-decouple==3.1 click==7.0 boto3==1.7.71 dockerflow==2018.4.0" \
    --optional-components=ANACONDA,JUPYTER \
    --project moz-fx-data-bq-srg \
    --region us-west1
