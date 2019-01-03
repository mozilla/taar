import hashlib
import time
import uuid

from flask import Flask
from flask import url_for

import pytest

from taar import ProfileFetcher
from taar import recommenders
from taar.context import default_context
from taar.profile_fetcher import ProfileController

try:
    from unittest.mock import MagicMock
except Exception:
    from mock import MagicMock


def hasher(uuid):
    return hashlib.new("sha256", str(uuid).encode("utf8")).hexdigest()


def create_recommendation_manager():
    root_ctx = default_context()
    pf = ProfileFetcher(root_ctx)
    pf.set_client(ProfileController(root_ctx, "us-west-2", "taar_addon_data_20180206"))
    root_ctx["profile_fetcher"] = pf
    r_factory = recommenders.RecommenderFactory(root_ctx.child())
    root_ctx["recommender_factory"] = r_factory
    rm = recommenders.RecommendationManager(root_ctx.child())
    return rm


@pytest.fixture
def app():
    from taar.plugin import configure_plugin
    from taar.plugin import PROXY_MANAGER

    flask_app = Flask("test")

    # Clobber the default recommendation manager with a MagicMock
    mock_recommender = MagicMock()
    PROXY_MANAGER.setResource(mock_recommender)

    configure_plugin(flask_app)

    return flask_app


def test_empty_results_by_default(client, app):
    # The default behaviour under test should be that the
    # RecommendationManager simply no-ops everything so we get back an
    # empty result list.
    res = client.post("/v1/api/recommendations/not_a_real_hash/")
    assert res.json == {"results": []}


@pytest.mark.skip("This is an integration test")
def test_mixed_and_promoted_and_taar_adodns(client, app):
    """
    Test that we can provide addon suggestions that also get clobbered
    by the promoted addon set.
    """
    pass


def test_only_promoted_addons_post(client, app):
    # POSTing a JSON blob allows us to specify promoted addons to the
    # TAAR service.
    res = client.post(
        "/v1/api/recommendations/not_a_real_hash/",
        json=dict(
            {"options": {"promoted": [["guid1", 10], ["guid2", 5], ["guid55", 8]]}}
        ),
        follow_redirects=True,
    )
    # The result should order the GUIDs in descending order of weight
    assert res.json == {"results": ["guid1", "guid55", "guid2"]}


@pytest.mark.skip("This is an integration test")
def test_recommenders(client_id="some_dev_client_id", branch="linear"):
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
    result = rm.recommend(client_id, limit=10, extra_data={"branch": branch})
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
        rm.recommend(client_id, limit=10, extra_data={"branch": branch_label})
    end = time.time()

    print(("%0.5f seconds per request" % ((end - start) / x)))


class FakeRecommendationManager(object):
    def __init__(self, *args, **kwargs):
        pass


class LocaleRecommendationManager(FakeRecommendationManager):
    def recommend(self, client_id, limit, extra_data={}):
        if extra_data.get("locale", None) == "en-US":
            return [("addon-Locale", 1.0)]
        return []


class EmptyRecommendationManager(FakeRecommendationManager):
    def recommend(self, client_id, limit, extra_data={}):
        return []


@pytest.fixture
def locale_recommendation_manager(monkeypatch):
    # Force the plugin configuration
    import os

    os.environ["TAAR_API_PLUGIN"] = "taar.plugin"

    import taar.flask_app

    taar.flask_app.APP_WRAPPER.set({"PROXY_RESOURCE": LocaleRecommendationManager()})


@pytest.fixture
def empty_recommendation_manager(monkeypatch):
    # Force the plugin configuration
    import os

    os.environ["TAAR_API_PLUGIN"] = "taar.plugin"

    import taar.flask_app

    taar.flask_app.APP_WRAPPER.set({"PROXY_RESOURCE": EmptyRecommendationManager()})


def test_empty_recommendation(client, empty_recommendation_manager):
    response = client.post(
        url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": []}'


def test_locale_recommendation(client, locale_recommendation_manager):
    response = client.post(
        url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
        + "?locale=en-US"
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": ["addon-Locale"]}'

    response = client.post(
        url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": []}'


@pytest.mark.skip("disabled until plugin system for taar-api is cleaned up")
def test_platform_recommendation(client, platform_recommendation_manager):
    uri = (
        url_for("recommendations", uuid_client_id=str(uuid.uuid4())) + "?platform=WOW64"
    )
    response = client.post(uri)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": ["addon-WOW64"]}'

    response = client.post(url_for("recommendations", uuid_client_id=uuid.uuid4()))
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": []}'


@pytest.mark.skip("disabled until plugin system for taar-api is cleaned up")
def test_intervention_a(client, static_recommendation_manager):
    url = url_for("recommendations", uuid_client_id=uuid.uuid4())
    response = client.post(url + "?branch=intervention-a")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    expected = b'{"results": ["intervention-a-addon-1", "intervention-a-addon-2", "intervention-a-addon-N"]}'
    assert response.data == expected


@pytest.mark.skip("disabled until plugin system for taar-api is cleaned up")
def test_intervention_b(client, static_recommendation_manager):
    url = url_for("recommendations", uuid_client_id=uuid.uuid4())
    response = client.post(url + "?branch=intervention_b")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    expected = b'{"results": ["intervention_b-addon-1", "intervention_b-addon-2", "intervention_b-addon-N"]}'
    assert response.data == expected


@pytest.mark.skip("disabled until plugin system for taar-api is cleaned up")
def test_control_branch(client, static_recommendation_manager):
    url = url_for("recommendations", uuid_client_id=uuid.uuid4())
    response = client.post(url + "?branch=control")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    expected = b'{"results": ["control-addon-1", "control-addon-2", "control-addon-N"]}'
    assert response.data == expected
