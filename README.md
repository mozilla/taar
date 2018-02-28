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
| 1 | [Legacy](taar/recommenders/legacy_recommender.py) | recommends WebExtensions based on the reported and disabled legacy add-ons | Telemetry data is available for the user and the user has at least one disabled add-on|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_legacy.py)|
| 2 | [Collaborative](taar/recommenders/collaborative_recommender.py) | recommends add-ons based on add-ons installed by other users (i.e. [collaborative filtering](https://en.wikipedia.org/wiki/Collaborative_filtering))|Telemetry data is available for the user and the user has at least one enabled add-on|[source](https://github.com/mozilla/telemetry-batch-view/blob/master/src/main/scala/com/mozilla/telemetry/ml/AddonRecommender.scala)|
| 3 | [Similarity](taar/recommenders/similarity_recommender.py) | recommends add-ons based on add-ons installed by similar representative users|Telemetry data is available for the user and a suitable representative donor can be found|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_similarity.py)|
| 4 | [Locale](taar/recommenders/locale_recommender.py) |recommends add-ons based on the top addons for the user's locale|Telemetry data is available for the user and the locale has enough users|[source](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_locale.py)|

## Instructions for releasing updates
New releases can be shipped by using the normal [github workflow](https://help.github.com/articles/creating-releases/). Once a new release is created, it will be automatically uploaded to `pypi`.


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
