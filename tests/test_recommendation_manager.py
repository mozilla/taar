# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.recommendation_manager import RecommendationManager
from taar.recommenders.base_recommender import AbstractRecommender

from .noop_fixtures import (
    noop_taarlocale_dataload,
    noop_taarcollab_dataload,
    noop_taarsimilarity_dataload,
    noop_taarlite_dataload,
)

from .mocks import MockRecommenderFactory

import operator
from functools import reduce

import numpy as np
from markus import TIMING
from markus.testing import MetricsMock

import mock
import contextlib
import fakeredis
from taar.recommenders.redis_cache import TAARCacheRedis


@contextlib.contextmanager
def mock_install_mock_curated_data(ctx):
    mock_data = []
    for i in range(20):
        mock_data.append(str(i) * 16)

    mock_ensemble_weights = {
        "ensemble_weights": {"collaborative": 1000, "similarity": 100, "locale": 10,}
    }

    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None

        stack.enter_context(
            mock.patch.object(TAARCacheRedis, "_fetch_whitelist", return_value=mock_data)
        )
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "_fetch_ensemble_weights",
                return_value=mock_ensemble_weights,
            )
        )

        stack = noop_taarlite_dataload(stack)
        stack = noop_taarcollab_dataload(stack)
        stack = noop_taarlocale_dataload(stack)
        stack = noop_taarsimilarity_dataload(stack)

        stack.enter_context(
            mock.patch.object(TAARCacheRedis, "_fetch_whitelist", return_value=mock_data)
        )

        # Patch fakeredis in
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "init_redis_connections",
                return_value={
                    0: fakeredis.FakeStrictRedis(db=0),
                    1: fakeredis.FakeStrictRedis(db=1),
                    2: fakeredis.FakeStrictRedis(db=2),
                },
            )
        )

        class DefaultMockProfileFetcher:
            def get(self, client_id):
                return {"client_id": client_id}

        mock_fetcher = DefaultMockProfileFetcher()

        ctx["profile_fetcher"] = mock_fetcher
        ctx["recommender_factory"] = MockRecommenderFactory()

        # Initialize redis
        TAARCacheRedis.get_instance(ctx).safe_load_data()

        yield stack


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


def test_none_profile_returns_empty_list(test_ctx):
    with mock_install_mock_curated_data(test_ctx):

        class MockProfileFetcher:
            def get(self, client_id):
                return None

        test_ctx["profile_fetcher"] = MockProfileFetcher()

        rec_manager = RecommendationManager(test_ctx)
        assert rec_manager.recommend("random-client-id", 10) == []


def test_simple_recommendation(test_ctx):
    # Fix the random seed so that we get stable results between test
    # runs
    np.random.seed(seed=42)

    with mock_install_mock_curated_data(test_ctx):
        EXPECTED_RESULTS = [
            ("def", 3320.0),
            ("klm", 409.99999999999994),
            ("hij", 3100.0),
            ("ijk", 3200.0),
            ("ghi", 3430.0),
            ("lmn", 420.0),
            ("jkl", 400.0),
            ("abc", 23.0),
            ("fgh", 22.0),
            ("efg", 21.0)
        ]

        with MetricsMock() as mm:
            manager = RecommendationManager(test_ctx)
            recommendation_list = manager.recommend("some_ignored_id", 10)

            assert isinstance(recommendation_list, list)
            assert recommendation_list == EXPECTED_RESULTS

            assert mm.has_record(TIMING, stat="taar.profile_recommendation")


def test_fixed_client_id_valid(test_ctx):
    with mock_install_mock_curated_data(test_ctx):
        manager = RecommendationManager(test_ctx)
        recommendation_list = manager.recommend("111111", 10)
        assert len(recommendation_list) == 10


def test_fixed_client_id_empty_list(test_ctx):
    class NoClientFetcher:
        def get(self, client_id):
            return None

    with mock_install_mock_curated_data(test_ctx):
        test_ctx["profile_fetcher"] = NoClientFetcher()

        manager = RecommendationManager(test_ctx)
        recommendation_list = manager.recommend("not_a_real_client_id", 10)

        assert len(recommendation_list) == 0


def test_experimental_randomization(test_ctx):
    with mock_install_mock_curated_data(test_ctx):

        manager = RecommendationManager(test_ctx)
        raw_list = manager.recommend("111111", 10)

        # Clobber the experiment probability to be 100% to force a
        # reordering.
        test_ctx["TAAR_EXPERIMENT_PROB"] = 1.0

        manager = RecommendationManager(test_ctx)
        rand_list = manager.recommend("111111", 10)

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
