from taar.profile_fetcher import ProfileFetcher
from taar.recommenders import RecommendationManager
from taar.recommenders.base_recommender import BaseRecommender


class MockProfileController:
    def __init__(self, mock_profile):
        self._profile = mock_profile

    def get_client_profile(self, client_id):
        return self._profile


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


def test_none_profile_returns_empty_list():
    fetcher = ProfileFetcher(MockProfileController(None))
    rec_manager = RecommendationManager(fetcher, ("fake-recommender", ))
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
    recommenders = (
        StubRecommender(False, []),
        StubRecommender(True, EXPECTED_ADDONS),
        StubRecommender(False, []),
    )

    # Make sure the recommender returns the expected addons.
    manager = RecommendationManager(StubFetcher(),
                                    recommenders)
    results = manager.recommend("client-id",
                                10,
                                extra_data={'branch': 'linear'})
    assert results == EXPECTED_ADDONS


def test_recommendation_ensemble():
    """The recommendation manager support an ensemble
    method.  We want to verify that at least the dispatch
    to the stub ensemble recommendation is correctly executing.
    """
    EXPECTED_ADDONS = [("ensemble_guid1", 0.1),
                       ("ensemble_guid2", 0.2),
                       ("ensemble_guid3", 0.3)]

    # Create a stub ProfileFetcher that always returns the same
    # client data.
    class StubFetcher:
        def get(self, client_id):
            return {'client_id': '00000'}

    # Configure the recommender so that only the second model
    # can recommend and return the expected addons.

    # Make sure the recommender returns the expected addons.
    manager = RecommendationManager(StubFetcher())
    results = manager.recommend("client-id",
                                10,
                                extra_data={'branch': 'ensemble'})
    assert results == EXPECTED_ADDONS
