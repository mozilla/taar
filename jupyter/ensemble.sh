#!/bin/bash

AWS_ACCESS_KEY_ID=AKIA5PV4VQIY4HJLNP4B
AWS_SECRET_ACCESS_KEY=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
requirements="mozilla-taar3==0.4.10 mozilla-srgutil==0.2.1 python-decouple==3.1 click==7.0 boto3==1.7.71 dockerflow==2018.4.0"

gcloud beta dataproc clusters create jupyter-ensemble-${RANDOM} \
    --bucket jupyter-ensemble \
    --enable-component-gateway \
    --image-version=1.4 \
    --initialization-actions gs://dataproc-initialization-actions/python/pip-install.sh \
    --master-machine-type=n1-standard-8 \
    --max-age=6h \
    --metadata "PIP_PACKAGES=${requirements}" \
    --num-workers=35 \
    --optional-components=ANACONDA,JUPYTER \
    --project moz-fx-data-bq-srg \
    --properties ^#^spark:spark.jars=gs://spark-lib/bigquery/spark-bigquery-latest.jar#spark:spark.hadoop.fs.s3a.access.key=${AWS_ACCESS_KEY_ID}#spark:spark.hadoop.fs.s3a.secret.key=${AWS_SECRET_ACCESS_KEY}#spark:spark.jars.packages=org.apache.spark:spark-avro_2.11:2.4.4#spark:spark.python.profile=true \
    --region us-west1 \
    --num-master-local-ssds=2 \
    --num-worker-local-ssds=2  \
    --worker-machine-type=n1-standard-8
