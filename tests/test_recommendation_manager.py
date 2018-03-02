# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.context import Context
from taar.cache import JSONCache, Clock

from taar.profile_fetcher import ProfileFetcher
from taar.recommenders import RecommendationManager
from taar.recommenders.base_recommender import AbstractRecommender
from .test_ensemblerecommender import Mocker
from .mocks import MockProfileController, MockRecommenderFactory


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


def get_test_ctx():
    fetcher = ProfileFetcher(MockProfileController(None))
    factory = MockRecommenderFactory()
    ctx = Context()
    ctx['profile_fetcher'] = fetcher
    ctx['recommender_factory'] = factory

    # Just populate the utils key for test when WeightCache is
    # instantiated
    ctx['utils'] = None
    return ctx.child()


def test_none_profile_returns_empty_list():
    ctx = get_test_ctx()
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    rec_manager = RecommendationManager(ctx)
    assert rec_manager.recommend("random-client-id", 10) == []


def test_recommendation_strategy():
    """The recommendation manager is currently very naive and just
    selects the first recommender which returns 'True' to
    can_recommend()."""

    EXPECTED_ADDONS = ["expected_id", "other-id"]

    # Create a stub ProfileFetcher that always returns the same
    # client data.
    class StubFetcher:
        def get(self, client_id):
            return {'client_id': '00000'}

    # Configure the recommender so that only the second model
    # can recommend and return the expected addons.
    factory = MockRecommenderFactory(legacy=lambda: StubRecommender(False, []),
                                     collaborative=lambda: StubRecommender(True, EXPECTED_ADDONS),
                                     similarity=lambda: StubRecommender(False, []),
                                     locale=lambda: StubRecommender(False, []))

    # Make sure the recommender returns the expected addons.
    ctx = get_test_ctx()
    ctx['recommender_factory'] = factory
    ctx['profile_fetcher'] = StubFetcher()
    ctx['utils'] = Mocker()
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    manager = RecommendationManager(ctx.child())
    results = manager.recommend("client-id",
                                10,
                                extra_data={'branch': 'linear'})
    assert results == EXPECTED_ADDONS


def test_recommendations_via_manager():  # noqa
    ctx = get_test_ctx()

    EXPECTED_RESULTS = [('ghi', 3430.0),
                        ('def', 3320.0),
                        ('ijk', 3200.0),
                        ('hij', 3100.0),
                        ('lmn', 420.0),
                        ('klm', 409.99999999999994),
                        ('jkl', 400.0),
                        ('abc', 23.0),
                        ('fgh', 22.0),
                        ('efg', 21.0)]

    factory = MockRecommenderFactory()

    class MockProfileFetcher:
        def get(self, client_id):
            return {'client_id': client_id}

    ctx['recommender_factory'] = factory
    ctx['profile_fetcher'] = MockProfileFetcher()
    ctx['utils'] = Mocker()
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    manager = RecommendationManager(ctx.child())
    recommendation_list = manager.recommend({'client_id': 'some_ignored_id'},
                                            10,
                                            extra_data={'branch': 'ensemble'})
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
