# Taar
Telemetry-Aware Addon Recommender

Table of Contents (ToC):
===========================

* [How does it work?](#how-does-it-work)
* [Supported models](#supported-models)
* [Instructions for Releasing Updates](#instructions-for-releasing-updates)

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
