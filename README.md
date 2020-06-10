# Taar
Telemetry-Aware Addon Recommender

[![Build Status](https://travis-ci.org/mozilla/taar.svg?branch=master)](https://travis-ci.org/mozilla/taar)

Table of Contents (ToC):
===========================

* [How does it work?](#how-does-it-work)
* [Supported models](#supported-models)
* [Instructions for Releasing Updates](#instructions-for-releasing-updates)
* [Building and Running tests](#build-and-run-tests)

## How does it work?
The recommendation strategy is implemented through the [RecommendationManager](taar/recommenders/recommendation_manager.py). Once a recommendation is requested for a specific [client id](https://firefox-source-docs.mozilla.org/toolkit/components/telemetry/telemetry/data/common-ping.html), the recommender iterates through all the registered models (e.g. [CollaborativeRecommender](taar/recommenders/collaborative_recommender.py)) linearly in their registered order. Results are returned from the first module that can perform a recommendation.

Each module specifies its own sets of rules and requirements and thus can decide if it can perform a recommendation independently from the other modules.

### Supported models
This is the ordered list of the currently supported models:

| Order | Model | Description | Conditions | Generator job |
|-------|-------|-------------|------------|---------------|
| 1 | [Collaborative](taar/recommenders/collaborative_recommender.py) | recommends add-ons based on add-ons installed by other users (i.e. [collaborative filtering](https://en.wikipedia.org/wiki/Collaborative_filtering))|Telemetry data is available for the user and the user has at least one enabled add-on|[source](https://github.com/mozilla/telemetry-batch-view/blob/master/src/main/scala/com/mozilla/telemetry/ml/AddonRecommender.scala)|
| 2 | [Similarity](taar/recommenders/similarity_recommender.py) &#42;| recommends add-ons based on add-ons installed by similar representative users|Telemetry data is available for the user and a suitable representative donor can be found|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_similarity.py)|
| 3 | [Locale](taar/recommenders/locale_recommender.py) |recommends add-ons based on the top addons for the user's locale|Telemetry data is available for the user and the locale has enough users|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_locale.py)|
| 4 | [Ensemble](taar/recommenders/ensemble_recommender.py) &#42;|recommends add-ons based on the combined (by [stacked generalization](https://en.wikipedia.org/wiki/Ensemble_learning#Stacking)) recomendations of other available recommender modules.|More than one of the other Models are available to provide recommendations.|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_ensemble.py)|

&#42; All jobs are scheduled in Mozilla's instance of [Airflow](https://github.com/mozilla/telemetry-airflow).  The Collaborative, Similarity and Locale jobs are executed on a [daily](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_daily.py) schedule, while the ensemble job is scheduled on a [weekly](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_weekly.py) schedule.

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

## A note on cdist optimization. 
cdist can speed up distance computation by a factor of 10 for the computations we're doing.
We can use it without problems on the canberra distance calculation.

Unfortunately there are multiple problems with it accepting a string array. There are different
problems in 0.18.1 (which is what is available on EMR), and on later versions. In both cases 
cdist attempts to convert a string to a double, which fails. For versions of scipy later than
0.18.1 this could be worked around with:

    distance.cdist(v1, v2, lambda x, y: distance.hamming(x, y))

However, when you manually provide a callable to cdist, cdist can not do it's baked in 
optimizations (https://github.com/scipy/scipy/blob/v1.0.0/scipy/spatial/distance.py#L2408)
so we can just apply the function `distance.hamming` to our array manually and get the same
performance.

## Build and run tests
You should be able to build taar using Python 2.7 or Python 3.5. To
run the testsuite, execute ::

```python
$ python setup.py develop
$ python setup.py test
```

Alternately, if you've got GNUMake installed, you can just run `make test` which will do all of that for you and run flake8 on the codebase.


There are additional integration tests and a microbenchmark available
in `tests/test_integration.py`.  See the source code for more
information.


## Pinning dependencies

TAAR uses hashin (https://pypi.org/project/hashin/) to pin SHA256
hashes for each dependency.  To update the hashes, you will need to
remove the run `make freeze` which forces all packages in the current
virtualenv to be written out to requirement.txt with versions and SHA
hashes.


## Required S3 dependencies


RecommendationManager:
  * s3://telemetry-parquet/telemetry-ml/addon_recommender/top_200_whitelist.json

Similarity Recommender:
  * s3://telemetry-parquet/taar/similarity/donors.json
  * s3://telemetry-parquet/taar/similarity/lr_curves.json

CollaborativeRecommender:
  * s3://telemetry-parquet/telemetry-ml/addon_recommender/item_matrix.json
  * s3://telemetry-parquet/telemetry-ml/addon_recommender/addon_mapping.json

LocaleRecommender:
  * s3://telemetry-parquet/taar/locale/top10_dict.json

EnsembleRecommender:
  * s3://telemetry-parquet/taar/ensemble/ensemble_weight.json



TAAR breaks out all S3 data load configuration into enviroment
variables.  This ensures that running under test has no chance of
clobbering the production data in the event that a developer has AWS
configuration keys installed locally in `~/.aws/`

Production enviroment variables required for TAAR

Collaborative Recommender ::

    TAAR_ITEM_MATRIX_BUCKET = "telemetry-parquet"
    TAAR_ITEM_MATRIX_KEY = "telemetry-ml/addon_recommender/item_matrix.json"

    TAAR_ADDON_MAPPING_BUCKET = "telemetry-parquet"
    TAAR_ADDON_MAPPING_KEY = "telemetry-ml/addon_recommender/addon_mapping.json"

Ensemble Recommender ::

    TAAR_ENSEMBLE_BUCKET = "telemetry-parquet"
    TAAR_ENSEMBLE_KEY = "taar/ensemble/ensemble_weight.json"

Locale Recommender ::

    TAAR_LOCALE_BUCKET = "telemetry-parquet"
    TAAR_LOCALE_KEY = "taar/locale/top10_dict.json"

Similarity Recommender ::

    TAAR_SIMILARITY_BUCKET = "telemetry-parquet"
    TAAR_SIMILARITY_DONOR_KEY = "taar/similarity/donors.json"
    TAAR_SIMILARITY_LRCURVES_KEY = "taar/similarity/lr_curves.json"
