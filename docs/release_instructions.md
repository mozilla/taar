## Instructions for releasing updates
Releases for TAAR are split across ETL jobs for Airflow and the
webservice that handles traffic coming from addons.mozilla.org.

ETL releases are subdivided further into 3 categories:

 1. Scala code that requires deployment by Java JAR file to a Dataproc environment
 2. PySpark code that requires deployment by a single monolithic script in the
    Dataproc enviroment.  These are stored in [telemetry-airflow/jobs]
and are autodeployed to gs://moz-fx-data-prod-airflow-dataproc-artifacts/jobs
 3. Python code that executes in a Google Kubernetes Engine (GKE)
    enviroment using a docker container image.

GKEPodOperator jobs:

* [taar_etl_.taar_amodump](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amodump.py)
* [taar_etl.taar_amowhitelist](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amowhitelist.py)
* [taar_etl.taar_update_whitelist](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_update_whitelist.py)

PySpark jobs for Dataproc: 

* [telemetry-airflow/jobs/taar_locale.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_locale.py)
* [telemetry-airflow/jobs/taar_similarity.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_similarity.py)
* [telemetry-airflow/jobs/taar_lite_guidguid.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_lite_guidguid.py)

Scala jobs for Dataproc
* [com.mozilla.telemetry.ml.AddonRecommender](https://github.com/mozilla/telemetry-batch-view/blob/master/src/main/scala/com/mozilla/telemetry/ml/AddonRecommender.scala) from telemetry-batch-view.jar


Jobs are scheduled in two separate DAGs in Airflow.

* [taar_daily](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_daily.py)
* [taar_weekly](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_weekly.py)

GKEPodOperator jobs must have code packaged up as containers for
execution in GKE.  Code can be found in the taar_gcp_etl repository.
Details to push containers into the GCP cloud repositories can be
found in the
[README.md](https://github.com/mozilla/taar_gcp_etl/blob/master/README.md)
in that repository.

PySpark jobs are maintained in the telemetry-airflow repository.  You
must take care to update the code in that repository and have it
merged to master for code to autodeploy.  Airflow execution will
always copy jobs out of the [jobs](https://github.com/mozilla/telemetry-airflow/tree/master/jobs)
into `gs://moz-fx-data-prod-airflow-dataproc-artifacts/`

The sole scala job remaining is part of the telemetry-batch-view
repository. Airflow will automatically use the latest code in the
master branch of `telemetry-batch-view`.
