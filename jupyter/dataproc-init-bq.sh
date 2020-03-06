#!/bin/bash

# You need to explicitly intall the spark-bigquery connector into the
# master spark node.
ROLE=$(/usr/share/google/get_metadata_value attributes/dataproc-role)
if [[ "${ROLE}" == 'Master' ]]; then
  gsutil cp gs://spark-lib/bigquery/spark-bigquery-latest.jar home/username
  gsutil cp gs://spark-lib/bigquery/spark-bigquery-latest.jar /usr/lib/spark/jars
fi
