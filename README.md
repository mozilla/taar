# Taar
Telemetry-Aware Addon Recommender

[![CircleCI](https://circleci.com/gh/mozilla/taar.svg?style=svg)](https://circleci.com/gh/mozilla/taar)


Table of Contents
=================

* [Taar](#taar)
  * [How does it work?](#how-does-it-work)
    * [Supported models](#supported-models)
  * [Build and run tests](#build-and-run-tests)
  * [Pinning dependencies](#pinning-dependencies)
  * [Instructions for releasing updates to production](#instructions-for-releasing-updates-to-production)
  * [Dependencies](#dependencies)
    * [AWS resources](#aws-resources)
    * [AWS enviroment configuration](#aws-enviroment-configuration)
  * [Collaborative Recommender](#collaborative-recommender)
  * [Ensemble Recommender](#ensemble-recommender)
  * [Locale Recommender](#locale-recommender)
  * [Similarity Recommender](#similarity-recommender)
  * [Google Cloud Platform resources](#google-cloud-platform-resources)
    * [Google Cloud BigQuery](#google-cloud-bigquery)
    * [Google Cloud Storage](#google-cloud-storage)
    * [Google Cloud BigTable](#google-cloud-bigtable)
  * [Production Configuration Settings](#production-configuration-settings)
  * [Deleting individual user data from all TAAR resources](#deleting-individual-user-data-from-all-taar-resources)
  * [Airflow enviroment configuration](#airflow-enviroment-configuration)
  * [Staging Enviroment](#staging-enviroment)
  * [A note on cdist optimization\.](#a-note-on-cdist-optimization)


## How does it work?
The recommendation strategy is implemented through the
[RecommendationManager](taar/recommenders/recommendation_manager.py).
Once a recommendation is requested for a specific [client
id](https://firefox-source-docs.mozilla.org/toolkit/components/telemetry/telemetry/data/common-ping.html),
the recommender iterates through all the registered models (e.g.
[CollaborativeRecommender](taar/recommenders/collaborative_recommender.py))
linearly in their registered order. Results are returned from the
first module that can perform a recommendation.

Each module specifies its own sets of rules and requirements and thus
can decide if it can perform a recommendation independently from the
other modules.

### Supported models
This is the ordered list of the currently supported models:

| Order | Model | Description | Conditions | Generator job |
|-------|-------|-------------|------------|---------------|
| 1 | [Collaborative](taar/recommenders/collaborative_recommender.py) | recommends add-ons based on add-ons installed by other users (i.e. [collaborative filtering](https://en.wikipedia.org/wiki/Collaborative_filtering))|Telemetry data is available for the user and the user has at least one enabled add-on|[source](https://github.com/mozilla/telemetry-batch-view/blob/master/src/main/scala/com/mozilla/telemetry/ml/AddonRecommender.scala)|
| 2 | [Similarity](taar/recommenders/similarity_recommender.py) | recommends add-ons based on add-ons installed by similar representative users|Telemetry data is available for the user and a suitable representative donor can be found|[source](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_similarity.py)|
| 3 | [Locale](taar/recommenders/locale_recommender.py) |recommends add-ons based on the top addons for the user's locale|Telemetry data is available for the user and the locale has enough users|[source](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_locale.py)|
| 4 | [Ensemble](taar/recommenders/ensemble_recommender.py) &#42;|recommends add-ons based on the combined (by [stacked generalization](https://en.wikipedia.org/wiki/Ensemble_learning#Stacking)) recomendations of other available recommender modules.|More than one of the other Models are available to provide recommendations.|[source](https://github.com/mozilla/telemetry-airflow/blob/master/jobs/taar_ensemble.py)|

All jobs are scheduled in Mozilla's instance of
[Airflow](https://github.com/mozilla/telemetry-airflow).  The
Collaborative, Similarity and Locale jobs are executed on a
[daily](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_daily.py)
schedule, while the ensemble job is scheduled on a
[weekly](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_weekly.py)
schedule.


## Build and run tests
You should be able to build taar using Python 3.5 or 3.7. 
To run the testsuite, execute ::

```python
$ python setup.py develop
$ python setup.py test
```

Alternately, if you've got GNUMake installed, a Makefile is included
with
[`build`](https://github.com/mozilla/taar/blob/more_docs/Makefile#L20)
and
[`test-container`](https://github.com/mozilla/taar/blob/more_docs/Makefile#L55)
targets.

You can just run `make
build; make test-container` which will build a complete Docker
container and run the test suite inside the container.

## Pinning dependencies

TAAR uses miniconda and a enviroment.yml file to manage versioning.

To update versions, edit the `enviroment.yml` with the new dependency
you need then run `make conda_update`.

If you are unfamiliar with using conda, see the [official
documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
for reference.

## Instructions for releasing updates to production

Building a new release of TAAR is fairly involved.  Documentation to
create a new release has been split out into separate
[instructions](https://github.com/mozilla/taar/blob/master/docs/release_instructions.md).


## Dependencies

### Google Cloud Storage resources

The final TAAR models are stored in:

```gs://moz-fx-data-taar-pr-prod-e0f7-prod-models```

The TAAR production model bucket is defined in Airflow under the
variable `taar_etl_model_storage_bucket`

Temporary models that the Airflow  ETL jobs require are stored in a
temporary bucket defined in the Airflow variable `taar_etl_storage_bucket`

Recommendation engines load models from GCS.

The following table is a complete list of all resources per
recommendation engine.

Recommendation Engine |  GCS Resource 
--- | ---
RecommendationManager Whitelist | gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/addon_recommender/only_guids_top_200.json.bz2
Similarity Recommender | gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/similarity/donors.json.bz2 <br> gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/similarity/lr_curves.json.bz2
CollaborativeRecommender |  gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/addon_recommender/item_matrix.json.bz2 <br> gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/addon_recommender/addon_mapping.json.bz2
LocaleRecommender | gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/locale/top10_dict.json.bz2
EnsembleRecommender | gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/ensemble/ensemble_weight.json.bz2
TAAR lite | gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/lite/guid_install_ranking.json.bz2 <br/> gs://moz-fx-data-taar-pr-prod-e0f7-prod-models/taar/lite/guid_coinstallation.json.bz2


# Production enviroment variables required for TAAR

## Collaborative Recommender

Env Variable | Value 
------- | --- 
TAAR_ITEM_MATRIX_BUCKET | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAAR_ITEM_MATRIX_KEY  | "addon_recommender/item_matrix.json.bz2"
TAAR_ADDON_MAPPING_BUCKET | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAAR_ADDON_MAPPING_KEY | "addon_recommender/addon_mapping.json.bz2"

## Ensemble Recommender

Env Variable | Value
--- | --- 
TAAR_ENSEMBLE_BUCKET  | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAAR_ENSEMBLE_KEY | "taar/ensemble/ensemble_weight.json.bz2"

## Locale Recommender

Env Variable | Value
--- | --- 
TAAR_LOCALE_BUCKET | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAAR_LOCALE_KEY | "taar/locale/top10_dict.json.bz2"

## Similarity Recommender

Env Variable | Value
--- | --- 
TAAR_SIMILARITY_BUCKET | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAAR_SIMILARITY_DONOR_KEY | "taar/similarity/donors.json.bz2"
TAAR_SIMILARITY_LRCURVES_KEY | "taar/similarity/lr_curves.json.bz2"


## TAAR Lite

Env Variable | Value
--- | --- 
TAARLITE_GUID_COINSTALL_BUCKET | "moz-fx-data-taar-pr-prod-e0f7-prod-models"
TAARLITE_GUID_COINSTALL_KEY | "taar/lite/guid_coinstallation.json.bz2"
TAARLITE_GUID_RANKING_KEY | "taar/lite/guid_install_ranking.json.bz2"


## Google Cloud Platform resources
### Google Cloud BigQuery

Cloud BigQuery uses the GCP project defined in Airflow in the
variable `taar_gcp_project_id`.

Dataset  
* `taar_tmp`

Table ID 
* `taar_tmp_profile`

Note that this table only exists for the duration of the taar_weekly
job, so there should be no need to manually manage this table.

### Google Cloud Storage 

The taar user profile extraction puts Avro format files into 
a GCS bucket defined by the following two variables in Airflow:

* `taar_gcp_project_id`
* `taar_etl_storage_bucket`

The bucket is automatically cleared at the *start* and *end* of
the TAAR weekly ETL job.

### Google Cloud BigTable 

The final TAAR user profile data is stored in a Cloud BigTable
instance defined by the following two variables in Airflow:

* `taar_gcp_project_id`
* `taar_bigtable_instance_id`

The table ID for user profile information is `taar_profile`.


------

## Production Configuration Settings

Production enviroment settings are stored in a [private repository](https://github.com/mozilla-services/cloudops-deployment/blob/master/projects/data/puppet/yaml/type/data.api.prod.taar.yaml).


## Deleting individual user data from all TAAR resources

Deletion of records in TAAR is fairly straight forward.  Once a user
disables telemetry from Firefox, all that is required is to delete
records from TAAR.

Deletion of records from the TAAR BigTable instance will remove the
client's list of addons from TAAR.  No further work is required.

Removal of the records from BigTable will cause JSON model updates to
no longer take the deleted record into account.  JSON models are
updated on a daily basis via the
[`taar_daily`](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_daily.py)

Updates in the weekly Airflow job in 
[`taar_weekly`](https://github.com/mozilla/telemetry-airflow/blob/master/dags/taar_weekly.py) only update the ensemble weights and the user profile information.

If the user profile information in `clients_last_seen` continues to
have data for the user's telemetry-id, TAAR will repopulate the user
profile data.  

Users who wish to remove their data from TAAR need to: 
1. Disable telemetry in Firefox
2. Have user telemetry data removed from all telemetry storage systems
   in GCP. Primarily this means the `clients_last_seen` table in
   BigQuery.
3. Have user data removed from BigTable.



## Airflow enviroment configuration

TAAR requires some configuration to be stored in Airflow variables for
the ETL jobs to run to completion correctly.

Airflow Variable | Value 
--- | ---
taar_gcp_project_id | The Google Cloud Platform project where BigQuery temporary tables, Cloud Storage buckets for Avro files and BigTable reside for TAAR.
taar_etl_storage_bucket | The Cloud Storage bucket name where temporary Avro files will reside when transferring data from BigQuery to BigTable. 
taar_bigtable_instance_id | The BigTable instance ID for TAAR user profile information
taar_dataflow_subnetwork | The subnetwork required to communicate between Cloud Dataflow


## Staging Enviroment

The staging enviroment of the TAAR service in GCP can be reached using
curl.

```
curl https://user@pass:stage.taar.nonprod.dataops.mozgcp.net/v1/api/recommendations/<hashed_telemetry_id>
```

Requests for a TAAR-lite recommendation can be made using curl as
well:

```
curl https://stage.taar.nonprod.dataops.mozgcp.net/taarlite/api/v1/addon_recommendations/<addon_guid>/
```


## TAARlite cache tools

There is a taarlite-redis tool to manage the taarlit redis cache.

The cache needs to be populated using the `--load` command or TAARlite
will return no results.

It is safe to reload new data while TAARlite is running - no
performance degradation is expected.

The cache contains a 'hot' buffer for reads and a 'cold' buffer to
write updated data to.

Subsequent invocations to `--load` will update the cache in the cold
buffer.  After data is successfully loaded, the hot and cold buffers
are swapped.

Running the the taarlite-redis tool inside the container:

```
$ docker run -it taar:latest bin/run python /opt/conda/bin/taarlite-redis.py --help

Usage: taarlite-redis.py [OPTIONS]

  Manage the TAARLite redis cache.

  This expecte that the following enviroment variables are set:

  REDIS_HOST REDIS_PORT

Options:
  --reset  Reset the redis cache to an empty state
  --load   Load data into redis
  --info   Display information about the cache state
  --help   Show this message and exit.
```


## Testing


TAARLite will respond with suggestions given an addon GUID.

A sample URL path may look like this:

`/taarlite/api/v1/addon_recommendations/uBlock0%40raymondhill.net/`

TAAR will treat any client ID with only repeating digits (ie: 0000) as
a test client ID and will return a dummy response.

A URL with the path : `/v1/api/recommendations/0000000000/` will
return a valid JSON result


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
