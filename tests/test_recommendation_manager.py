# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import json
from moto import mock_s3
from taar.recommenders import RecommendationManager
from taar.recommenders import TEST_CLIENT_IDS, EMPTY_TEST_CLIENT_IDS
from taar.recommenders.base_recommender import AbstractRecommender

from taar.recommenders.ensemble_recommender import (
    TAAR_ENSEMBLE_BUCKET,
    TAAR_ENSEMBLE_KEY,
)


from .mocks import MockRecommenderFactory
from .test_hybrid_recommender import install_mock_curated_data

import operator
from functools import reduce


class StubRecommender(AbstractRecommender):
    """ A shared, stub recommender that can be used for testing.
    """

    def __init__(self, can_recommend, stub_recommendations):
        self._can_recommend = can_recommend
        self._recommendations = stub_recommendations

    def can_recommend(self, client_info, extra_data={}):
        return self._can_recommend

    def recommend(self, client_data, limit, extra_data={}):
        return self._recommendations


def install_mocks(ctx):
    class MockProfileFetcher:
        def get(self, client_id):
            return {"client_id": client_id}

    ctx.set("profile_fetcher", MockProfileFetcher())
    ctx.set("recommender_factory", MockRecommenderFactory())

    DATA = {
        "ensemble_weights": {
            "collaborative": 1000,
            "similarity": 100,
            "locale": 10,
        }
    }

    conn = boto3.resource("s3", region_name="us-west-2")
    conn.create_bucket(Bucket=TAAR_ENSEMBLE_BUCKET)
    conn.Object(TAAR_ENSEMBLE_BUCKET, TAAR_ENSEMBLE_KEY).put(
        Body=json.dumps(DATA)
    )

    return ctx


@mock_s3
def test_none_profile_returns_empty_list(test_ctx):
    ctx = install_mocks(test_ctx)

    class MockProfileFetcher:
        def get(self, client_id):
            return None

    ctx.set("profile_fetcher", MockProfileFetcher())

    rec_manager = RecommendationManager(ctx)
    assert rec_manager.recommend("random-client-id", 10) == []


@mock_s3
def test_simple_recommendation(test_ctx):
    ctx = install_mocks(test_ctx)

    EXPECTED_RESULTS = [
        ("ghi", 3430.0),
        ("def", 3320.0),
        ("ijk", 3200.0),
        ("hij", 3100.0),
        ("lmn", 420.0),
        ("klm", 409.99999999999994),
        ("jkl", 400.0),
        ("abc", 23.0),
        ("fgh", 22.0),
        ("efg", 21.0),
    ]

    manager = RecommendationManager(ctx)
    recommendation_list = manager.recommend("some_ignored_id", 10)

    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS


@mock_s3
def test_fixed_client_id_valid(test_ctx):
    ctx = install_mocks(test_ctx)
    ctx = install_mock_curated_data(ctx)

    manager = RecommendationManager(ctx)
    recommendation_list = manager.recommend(TEST_CLIENT_IDS[0], 10)

    assert len(recommendation_list) == 10


@mock_s3
def test_fixed_client_id_empty_list(test_ctx):
    ctx = install_mocks(test_ctx)
    ctx = install_mock_curated_data(ctx)

    manager = RecommendationManager(ctx)
    recommendation_list = manager.recommend(EMPTY_TEST_CLIENT_IDS[0], 10)

    assert len(recommendation_list) == 0


@mock_s3
def test_experimental_randomization(test_ctx):
    ctx = install_mocks(test_ctx)
    ctx = install_mock_curated_data(ctx)

    manager = RecommendationManager(ctx)
    raw_list = manager.recommend(TEST_CLIENT_IDS[0], 10)

    # Clobber the experiment probability to be 100% to force a
    # reordering.
    ctx.set("TAAR_EXPERIMENT_PROB", 1.0)

    manager = RecommendationManager(ctx)
    rand_list = manager.recommend(TEST_CLIENT_IDS[0], 10)

    """
    The two lists should be :

    * different (guid, weight) lists (possibly just order)
    * same length
    """
    assert (
        reduce(
            operator.and_,
            [
                (t1[0] == t2[0] and t1[1] == t2[1])
                for t1, t2 in zip(rand_list, raw_list)
            ],
        )
        is False
    )
    assert len(rand_list) == len(raw_list)
