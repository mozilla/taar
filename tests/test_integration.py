import pytest
from taar.context import default_context
from taar import ProfileController, ProfileFetcher
from taar import recommenders


@pytest.mark.skip("This is an integration test")
def test_recommenders(client_id='some_dev_client_id', branch='linear'):
    root_ctx = default_context()
    client = ProfileController('us-west-2', 'taar_addon_data_20180206')
    pf = ProfileFetcher(client)
    root_ctx['profile_fetcher'] = pf
    r_factory = recommenders.RecommenderFactory(root_ctx.child())
    root_ctx['recommender_factory'] = r_factory
    rm = recommenders.RecommendationManager(root_ctx.child())
    result = rm.recommend(client_id, limit=10, extra_data={'branch': branch})
    print(result)
    return result
