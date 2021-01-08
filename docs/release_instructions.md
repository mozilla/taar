# Instructions for releasing updates

## Overview

Releases for TAAR are split across ETL jobs for Airflow and the
webservice that handles traffic coming from addons.mozilla.org.

You may or may not need to upgrade all parts at once.

### ETL release instructions

ETL releases are subdivided further into 3 categories:

 1. Scala code that requires deployment by Java JAR file to a Dataproc environment
 2. PySpark code that requires deployment by a single monolithic script in the
    Dataproc enviroment.  These are stored in [telemetry-airflow/jobs]
and are autodeployed to gs://moz-fx-data-prod-airflow-dataproc-artifacts/jobs
 3. Python code that executes in a Google Kubernetes Engine (GKE)
    enviroment using a docker container image.
 4. TAAR User profile information

#### 1. Scala jobs for Dataproc
* [com.mozilla.telemetry.ml.AddonRecommender](https://github.com/mozilla/telemetry-batch-view/blob/master/src/main/scala/com/mozilla/telemetry/ml/AddonRecommender.scala) from telemetry-batch-view.jar

#### 2. PySpark jobs for Dataproc

* [telemetry-airflow/jobs/taar_locale.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_locale.py)
* [telemetry-airflow/jobs/taar_similarity.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_similarity.py)
* [telemetry-airflow/jobs/taar_lite_guidguid.py](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_lite_guidguid.py)

#### 3. GKEPodOperator jobs

* [taar_etl_.taar_amodump](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amodump.py)
* [taar_etl.taar_amowhitelist](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_amowhitelist.py)
* [taar_etl.taar_update_whitelist](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_update_whitelist.py)


#### 4. TAAR User profile information

The TAAR User profile information is stored in Cloud BigTable.  The
job is run as a list of idempotent steps. All tasks are contained in
a single file at:

* [taar_etl.taar_profile_bigtable](https://github.com/mozilla/taar_gcp_etl/blob/master/taar_etl/taar_profile_bigtable.py)


## Jobs are scheduled in two separate DAGs in Airflow.

* [taar_daily](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_daily.py)
* [taar_weekly](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_weekly.py)


### Updating code for GKEPodOperator jobs

G#KEPodOperator jobs must have code packaged up as containers for
execution in GKE.  Code can be found in the taar_gcp_etl repository.
Detailed build instructions can be found in the 
[README.md](https://github.com/mozilla/taar_gcp_etl/blob/master/README.md)
in that repository.

Generally, if you tag a revision in `taar_gcp_etl` - CircleCI will build the production
container for you automatically.  You will also need to update the
container tag in the `taar_daily` or `taar_weekly` DAGs.

### Updating code for PySpark jobs

PySpark jobs are maintained in the telemetry-airflow repository.  You
must take care to update the code in that repository and have it
merged to master for code to autodeploy into the production Airflow instance.  


Airflow execution will always copy jobs out of the
[jobs](https://github.com/mozilla/telemetry-airflow/tree/master/jobs)
into `gs://moz-fx-data-prod-airflow-dataproc-artifacts/`

### Updating code for the Scala ETL job

The sole scala job remaining is part of the telemetry-batch-view
repository. Airflow will automatically use the latest code in the
master branch of `telemetry-batch-view`.


## Deploying TAAR the webservice

The TAAR webservice is setup as a single container with no dependant
containers.  If you are familiar with earlier versions of TAAR, you
may be expecting redis servers to also be required - this is no longer
the case.  Models are sufficiently small that they can held in memory.

Tagging a version in git will trigger CircleCI to build a container
image for production.  

Autopush on tag is currently enabled for staging environment.

You must inform operations to push the tag to production enviroment.  



## A note about logging

tl;dr - Do **NOT** use python's logging module for any logging in the TAAR
repository.  TAAR's recommendation code is used by the ETL jobs - some
of which execute inside a PySpark enviroment and logging is
incompatible with PySpark.

PySpark distributes executable objects across the spark worker nodes
by pickling live objects.  Unfortunately, Python uses non-serizable
mutexes in the logging module which was not fixed until python 3.8.

See the https://bugs.python.org/issue30520 for details.

You cannot upgrade TAAR to use Python 3.8 either, as the full
numerical computation stack of PySpark, numpy, scipy, sklearn do not
properly support Python 3.8.

So again -just **don't use python logging**.
