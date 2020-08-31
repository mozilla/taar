# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.ensemble_recommender import (
    WeightCache,
    EnsembleRecommender,
)
from taar.settings import (
    TAAR_ENSEMBLE_BUCKET,
    TAAR_ENSEMBLE_KEY,
    TAAR_WHITELIST_BUCKET,
    TAAR_WHITELIST_KEY,
)
from moto import mock_s3
import boto3
import json
from .mocks import MockRecommenderFactory

from markus import TIMING
from markus.testing import MetricsMock

EXPECTED = {"collaborative": 1000, "similarity": 100, "locale": 10}


def install_mock_ensemble_data(ctx):
    DATA = {"ensemble_weights": EXPECTED}

    conn = boto3.resource("s3", region_name="us-west-2")
    conn.create_bucket(Bucket=TAAR_ENSEMBLE_BUCKET)
    conn.Object(TAAR_ENSEMBLE_BUCKET, TAAR_ENSEMBLE_KEY).put(Body=json.dumps(DATA))

    conn.create_bucket(Bucket=TAAR_WHITELIST_BUCKET)
    conn.Object(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY).put(
        Body=json.dumps(
            [
                "2.0@disconnect.me",
                "@contain-facebook",
                "@testpilot-containers",
                "CookieAutoDelete@kennydo.com",
                "FirefoxColor@mozilla.com",
                "adblockultimate@adblockultimate.net",
                "addon@darkreader.org",
                "adguardadblocker@adguard.com",
                "adnauseam@rednoise.org",
                "clearcache@michel.de.almeida",
                "copyplaintext@eros.man",
                "default-bookmark-folder@gustiaux.com",
                "enhancerforyoutube@maximerf.addons.mozilla.org",
                "extension@one-tab.com",
                "extension@tabliss.io",
                "firefox-addon@myki.co",
                "firefox@ghostery.com",
                "forecastfox@s3_fix_version",
                "forget-me-not@lusito.info",
                "foxyproxy@eric.h.jung",
                "foxytab@eros.man",
                "gmailnoads@mywebber.com",
            ]
        )
    )

    return ctx


@mock_s3
def test_weight_cache(test_ctx):
    ctx = install_mock_ensemble_data(test_ctx)
    wc = WeightCache(ctx)
    actual = wc.getWeights()
    assert EXPECTED == actual


@mock_s3
def test_recommendations(test_ctx):
    with MetricsMock() as mm:
        ctx = install_mock_ensemble_data(test_ctx)

        EXPECTED_RESULTS = [
            ("ghi", 3430.0),
            ("def", 3320.0),
            ("ijk", 3200.0),
            ("hij", 3100.0),
            ("lmn", 420.0),
        ]

        factory = MockRecommenderFactory()
        ctx["recommender_factory"] = factory

        ctx["recommender_map"] = {
            "collaborative": factory.create("collaborative"),
            "similarity": factory.create("similarity"),
            "locale": factory.create("locale"),
        }
        r = EnsembleRecommender(ctx.child())
        client = {"client_id": "12345"}  # Anything will work here

        recommendation_list = r.recommend(client, 5)
        assert isinstance(recommendation_list, list)
        assert recommendation_list == EXPECTED_RESULTS

        assert mm.has_record(TIMING, "taar.ensemble")
        assert mm.has_record(TIMING, "taar.ensemble_recommend")


@mock_s3
def test_preinstalled_guids(test_ctx):
    ctx = install_mock_ensemble_data(test_ctx)

    EXPECTED_RESULTS = [
        ("ghi", 3430.0),
        ("ijk", 3200.0),
        ("lmn", 420.0),
        ("klm", 409.99999999999994),
        ("abc", 23.0),
    ]

    factory = MockRecommenderFactory()
    ctx["recommender_factory"] = factory

    ctx["recommender_map"] = {
        "collaborative": factory.create("collaborative"),
        "similarity": factory.create("similarity"),
        "locale": factory.create("locale"),
    }
    r = EnsembleRecommender(ctx.child())

    # 'hij' should be excluded from the suggestions list
    # The other two addon GUIDs 'def' and 'jkl' will never be
    # recommended anyway and should have no impact on results
    client = {"client_id": "12345", "installed_addons": ["def", "hij", "jkl"]}

    recommendation_list = r.recommend(client, 5)
    print(recommendation_list)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS


@mock_s3
def test_mock_client_ids(test_ctx):
    ctx = install_mock_ensemble_data(test_ctx)

    EXPECTED_RESULTS = [
        ("2.0@disconnect.me", 0.17),
        ("@contain-facebook", 0.25),
        ("@testpilot-containers", 0.72),
        ("CookieAutoDelete@kennydo.com", 0.37),
        ("FirefoxColor@mozilla.com", 0.32),
    ]

    factory = MockRecommenderFactory()
    ctx["recommender_factory"] = factory

    ctx["recommender_map"] = {
        "collaborative": factory.create("collaborative"),
        "similarity": factory.create("similarity"),
        "locale": factory.create("locale"),
    }
    r = EnsembleRecommender(ctx.child())

    # 'hij' should be excluded from the suggestions list
    # The other two addon GUIDs 'def' and 'jkl' will never be
    # recommended anyway and should have no impact on results
    client = {"client_id": "11111"}

    recommendation_list = r.recommend(client, 5)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
