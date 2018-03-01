import pytest
from taar.context import default_context
from taar import ProfileController, ProfileFetcher
from taar import recommenders
import time


def create_recommendation_manager():
    root_ctx = default_context()
    client = ProfileController('us-west-2', 'taar_addon_data_20180206')
    pf = ProfileFetcher(client)
    root_ctx['profile_fetcher'] = pf
    r_factory = recommenders.RecommenderFactory(root_ctx.child())
    root_ctx['recommender_factory'] = r_factory
    rm = recommenders.RecommendationManager(root_ctx.child())
    return rm


@pytest.mark.skip("This is an integration test")
def test_recommenders(client_id='some_dev_client_id', branch='linear'):
    """
    This integration test can be used to drive the TAAR
    RecommendationManager from your machine.  This assumes you have
    access to the proper dev IAM roles to read the S3 buckets.

    Note that the RecommendationManager emits addon GUID and a weight.
    The taar-api webservice does not display the weights in the JSON
    output.

    You can drive taar in your virtualenv with ipython like this :

            Victors-MacBook-Pro-2:~ victorng$ cd dev/taar
            Victors-MacBook-Pro-2:taar victorng$ workon taar
            (taar) Victors-MacBook-Pro-2:taar victorng$ ipython
            Python 3.5.4 (default, Jan 11 2018, 09:58:51)
            Type 'copyright', 'credits' or 'license' for more information
            IPython 6.2.1 -- An enhanced Interactive Python. Type '?' for help.

            In [1]: client_id = '6d93e4e9-96ca-433d-a4a9-92efd0da8957'

            In [2]: from tests.test_integration import test_recommenders

            In [3]: test_recommenders(client_id=client_id, branch='ensemble')
            Out[3]:
            [('uBlock0@raymondhill.net', 2.11520519710274),
             ('YoutubeDownloader@PeterOlayev.com', 2.09866473),
             ('artur.dubovoy@gmail.com', 2.09866473),
             ('enhancerforyoutube@maximerf.addons.mozilla.org', 2.09866473),
             ('jid1-NIfFY2CA8fy1tg@jetpack', 2.09866473),
             ('translator@zoli.bod', 2.09866473),
             ('{b9db16a4-6edc-47ec-a1f4-b86292ed211d}', 2.09866473),
             ('{bee6eb20-01e0-ebd1-da83-080329fb9a3a}', 2.09866473),
             ('{d10d0bf8-f5b5-c8b4-a8b2-2b9879e08c5d}', 2.09866473),
             ('{e4a8a97b-f2ed-450b-b12d-ee082ba24781}', 2.09866473)]

            In [4]:
    """
    rm = create_recommendation_manager()
    result = rm.recommend(client_id, limit=10, extra_data={'branch': branch})
    return result


def micro_bench(x, client_id, branch_label):
    """
    Run a microbenchmark against the recommendation manager.

    This should really be run in an AWS enviroment so that you're not
    hitting as much network latency when running from your local
    laptop.
    """
    rm = create_recommendation_manager()
    start = time.time()
    for i in range(x):
        rm.recommend(client_id, limit=10, extra_data={'branch': branch_label})
    end = time.time()

    print(("%0.5f seconds per request" % ((end - start) / x)))
