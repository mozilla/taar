from taar.profile_fetcher import ProfileFetcher
from taar.recommenders import RecommendationManager
from taar import hbase_client


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
