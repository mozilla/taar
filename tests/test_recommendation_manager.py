from taar.profile_fetcher import ProfileFetcher
from taar.recommenders import RecommendationManager
from taar.recommenders.base_recommender import BaseRecommender
from taar import hbase_client


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


def test_none_profile_returns_empty_list(monkeypatch):
    monkeypatch.setattr(hbase_client.HBaseClient,
                        'get_client_profile',
                        lambda x, y: None)

    monkeypatch.setattr(hbase_client.HBaseClient,
                        '_get_hbase_hostname',
                        lambda x: 'master-ip-address')

    fetcher = ProfileFetcher()

    rec_manager = RecommendationManager(fetcher, ("fake-recommender", ))
    assert rec_manager.recommend("random-client-id", 10) == []


def test_recommendation_strategy():
    EXPECTED_ADDONS = ["expected_id", "other-id"]

    # Create a stub ProfileFetcher that always returns the same
    # client data.
    class StubFetcher:
        def get(self, client_id):
            return {}

    # Configure the recommender so that only the second model
    # can recommend and return the expected addons.
    recommenders = (
        StubRecommender(False, []),
        StubRecommender(True, EXPECTED_ADDONS),
        StubRecommender(False, []),
    )

    # Make sure the recommender returns the expected addons.
    manager = RecommendationManager(StubFetcher(), recommenders)
    assert manager.recommend("client-id", 10) == EXPECTED_ADDONS
