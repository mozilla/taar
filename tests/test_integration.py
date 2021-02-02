import hashlib
import logging
import uuid

from flask import Flask
from flask import url_for

import pytest

from taar.recommenders.redis_cache import TAARCacheRedis
from taar.settings import TAARLITE_MAX_RESULTS
from taar.context import default_context
from .test_guid_based_recommender import mock_coinstall_ranking_context

try:
    from unittest.mock import MagicMock
except Exception:
    from mock import MagicMock


def hasher(uuid):
    return hashlib.new("sha256", str(uuid).encode("utf8")).hexdigest()


@pytest.fixture
def app():

    from taar.plugin import configure_plugin
    from taar.plugin import PROXY_MANAGER

    flask_app = Flask("test")

    # Clobber the default recommendation manager with a MagicMock
    mock_recommender = MagicMock()
    PROXY_MANAGER.setTaarRM(mock_recommender)

    configure_plugin(flask_app)

    return flask_app


def test_empty_results_by_default(client, app):
    # The default behaviour under test should be that the
    # RecommendationManager simply no-ops everything so we get back an
    # empty result list.
    res = client.post("/v1/api/recommendations/not_a_real_hash/")
    assert res.json == {"results": []}


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


class FakeRecommendationManager(object):
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger('test')


class StaticRecommendationManager(FakeRecommendationManager):

    # Recommenders must return a list of 2-tuple results
    # with (GUID, weight)
    def recommend(self, client_id, limit, extra_data={}):
        result = [
            ("test-addon-1", 1.0),
            ("test-addon-2", 1.0),
            ("test-addon-N", 1.0),
        ]
        return result


class LocaleRecommendationManager(FakeRecommendationManager):
    def recommend(self, client_id, limit, extra_data={}):
        if extra_data.get("locale", None) == "en-US":
            return [("addon-Locale", 1.0)]
        return []


class EmptyRecommendationManager(FakeRecommendationManager):
    def recommend(self, client_id, limit, extra_data={}):
        return []


class PlatformRecommendationManager(FakeRecommendationManager):
    def recommend(self, client_id, limit, extra_data={}):
        if extra_data.get("platform", None) == "WOW64":
            return [("addon-WOW64", 1.0)]
        return []


class ProfileFetcherEnabledRecommendationManager(FakeRecommendationManager):
    def __init__(self, *args, **kwargs):
        self._ctx = default_context(TAARCacheRedis)
        self._ctx["profile_fetcher"] = kwargs["profile_fetcher"]
        super(ProfileFetcherEnabledRecommendationManager, self).__init__(args, kwargs)


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


@pytest.fixture
def platform_recommendation_manager(monkeypatch):
    # Force the plugin configuration
    import os

    os.environ["TAAR_API_PLUGIN"] = "taar.plugin"

    import taar.flask_app

    taar.flask_app.APP_WRAPPER.set({"PROXY_RESOURCE": PlatformRecommendationManager()})


@pytest.fixture
def static_recommendation_manager(monkeypatch):
    # Force the plugin configuration
    import os

    os.environ["TAAR_API_PLUGIN"] = "taar.plugin"

    import taar.flask_app

    taar.flask_app.APP_WRAPPER.set({"PROXY_RESOURCE": StaticRecommendationManager()})


@pytest.fixture
def profile_enabled_rm(monkeypatch):
    # Force the plugin configuration
    import os

    os.environ["TAAR_API_PLUGIN"] = "taar.plugin"

    import taar.flask_app

    mock_profile = {"installed_addons": ["addon_119", "addon_219"]}

    class MockPF:
        def get(self, hashed_client_id):
            return mock_profile

    pf = MockPF()
    pfm = ProfileFetcherEnabledRecommendationManager(profile_fetcher=pf)
    taar.flask_app.APP_WRAPPER.set({"PROXY_RESOURCE": pfm})


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


def test_platform_recommendation(client, platform_recommendation_manager):
    uri = (
        url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
        + "?platform=WOW64"
    )
    response = client.post(uri)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": ["addon-WOW64"]}'

    response = client.post(
        url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.data == b'{"results": []}'


def test_simple_request(client, static_recommendation_manager):
    url = url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    response = client.post(url)
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    expected = b'{"results": ["test-addon-1", "test-addon-2", "test-addon-N"]}'
    assert response.data == expected


def test_mixed_and_promoted_and_taar_adodns(client, static_recommendation_manager):
    """
    Test that we can provide addon suggestions that also get clobbered
    by the promoted addon set.
    """
    url = url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    res = client.post(
        url,
        json=dict(
            {"options": {"promoted": [["guid1", 10], ["guid2", 5], ["guid55", 8]]}}
        ),
        follow_redirects=True,
    )
    # The result should order the GUIDs in descending order of weight
    expected = {
        "results": [
            "guid1",
            "guid55",
            "guid2",
            "test-addon-1",
            "test-addon-2",
            "test-addon-N",
        ]
    }
    assert res.json == expected


def test_overlapping_mixed_and_promoted_and_taar_adodns(
    client, static_recommendation_manager
):
    """
    Test that we can provide addon suggestions that also get clobbered
    by the promoted addon set.
    """
    url = url_for("recommendations", hashed_client_id=hasher(uuid.uuid4()))
    res = client.post(
        url,
        json=dict(
            {
                "options": {
                    "promoted": [["test-addon-1", 10], ["guid2", 5], ["guid55", 8],]
                }
            }
        ),
        follow_redirects=True,
    )
    # The result should order the GUIDs in descending order of weight
    expected = {
        "results": ["test-addon-1", "guid55", "guid2", "test-addon-2", "test-addon-N",]
    }
    assert res.json == expected


def test_client_addon_lookup_no_client(client, profile_enabled_rm):
    """
    test that we can see if a client has an addon installed
    """
    hashed_client_id = hasher(uuid.uuid4())
    addon_id = "abc123"

    url = url_for(
        "client_has_addon", hashed_client_id=hashed_client_id, addon_id=addon_id
    )
    res = client.get(url, follow_redirects=True)

    _ = {"results": False}
    assert res.json["results"] is False


def test_client_has_addon(client, profile_enabled_rm):
    """
    test that we can see if a client has an addon installed
    """

    hashed_client_id = hasher(uuid.uuid4())
    addon_id = "addon_119"

    url = url_for(
        "client_has_addon", hashed_client_id=hashed_client_id, addon_id=addon_id
    )
    res = client.get(url, follow_redirects=True)

    expected = {"results": True}
    assert res.json == expected


def test_client_has_no_addon(client, profile_enabled_rm):
    """
    test that we can see if a client has an addon installed
    """

    hashed_client_id = hasher(uuid.uuid4())
    addon_id = "addon_984932434"

    url = url_for(
        "client_has_addon", hashed_client_id=hashed_client_id, addon_id=addon_id
    )
    res = client.get(url, follow_redirects=True)

    assert res.json["results"] is False


def test_taarlite(client, test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING):
    """
    Check that the result size of taarlite is TAARLITE_MAX_RESULTS
    """

    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):

        url = url_for("taarlite_recommendations", guid="guid-1",)
        res = client.get(url, follow_redirects=True)

        assert len(res.json["results"]) == TAARLITE_MAX_RESULTS
        assert res.json["results"] == ["guid-5", "guid-6", "guid-3", "guid-2"]
