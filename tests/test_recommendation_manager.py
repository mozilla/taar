from taar.profile_fetcher import ProfileFetcher
from taar.recommenders import RecommendationManager
from taar.recommenders.base_recommender import BaseRecommender
from .mocks import MockProfileController, MockRecommenderFactory
from .mocks import mock_s3_ensemble_weights  # noqa


class StubRecommender(BaseRecommender):
    """ A shared, stub recommender that can be used for testing.
    """
    def __init__(self, can_recommend, stub_recommendations):
        self._can_recommend = can_recommend
        self._recommendations = stub_recommendations

    def can_recommend(self, client_info, extra_data={}):
        return self._can_recommend

    def recommend(self, client_data, limit, extra_data={}):
        return self._recommendations


def test_none_profile_returns_empty_list(mock_s3_ensemble_weights): # noqa
    fetcher = ProfileFetcher(MockProfileController(None))
    factory = MockRecommenderFactory()
    rec_manager = RecommendationManager(factory, fetcher)
    assert rec_manager.recommend("random-client-id", 10) == []


def test_recommendation_strategy(mock_s3_ensemble_weights):  # noqa
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
    manager = RecommendationManager(factory, StubFetcher())
    results = manager.recommend("client-id",
                                10,
                                extra_data={'branch': 'linear'})
    assert results == EXPECTED_ADDONS


def test_recommendations_via_manager(mock_s3_ensemble_weights):  # noqa
    EXPECTED_RESULTS = [('cde', 12000.0),
                        ('bcd', 11000.0),
                        ('abc', 10023.0),
                        ('ghi', 3430.0),
                        ('def', 3320.0),
                        ('ijk', 3200.0),
                        ('hij', 3100.0),
                        ('lmn', 420.0),
                        ('klm', 409.99999999999994),
                        ('jkl', 400.0)]

    factory = MockRecommenderFactory()

    class MockProfileFetcher:
        def get(self, client_id):
            return {'client_id': client_id}

    manager = RecommendationManager(factory, MockProfileFetcher())
    recommendation_list = manager.recommend('some_ignored_id', 10, extra_data={'branch': 'ensemble'})
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
