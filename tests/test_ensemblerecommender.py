# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from taar.interfaces import ITAARCache
from taar.recommenders.ensemble_recommender import EnsembleRecommender
import mock
import contextlib
import fakeredis
from taar.recommenders.redis_cache import TAARCacheRedis
from .noop_fixtures import (
    noop_taarlocale_dataload,
    noop_taarcollab_dataload,
    noop_taarlite_dataload,
    noop_taarsimilarity_dataload,
)
from .mocks import MockRecommenderFactory

from markus import TIMING
from markus.testing import MetricsMock

EXPECTED = {"collaborative": 1000, "similarity": 100, "locale": 10}


def noop_loaders(stack):
    stack = noop_taarlocale_dataload(stack)
    stack = noop_taarcollab_dataload(stack)
    stack = noop_taarlite_dataload(stack)
    stack = noop_taarsimilarity_dataload(stack)
    return stack


@contextlib.contextmanager
def mock_install_mock_ensemble_data(ctx):
    DATA = {"ensemble_weights": EXPECTED}

    WHITELIST_DATA = [
        "2.0@disconnect.me",
        "@contain-facebook",
        "@testpilot-containers",
        "CookieAutoDelete@kennydo.com",
        "FirefoxColor@mozilla.com",
        "adblockultimate@adblockultimate.net",
        "addon@darkreader.org",
        "adguardadblocker@adguard.com",
        "adnauseam@rednoise.org",
        "clearcache@michel.de.almeida",
        "copyplaintext@eros.man",
        "default-bookmark-folder@gustiaux.com",
        "enhancerforyoutube@maximerf.addons.mozilla.org",
        "extension@one-tab.com",
        "extension@tabliss.io",
        "firefox-addon@myki.co",
        "firefox@ghostery.com",
        "forecastfox@s3_fix_version",
        "forget-me-not@lusito.info",
        "foxyproxy@eric.h.jung",
        "foxytab@eros.man",
        "gmailnoads@mywebber.com",
    ]

    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None
        stack.enter_context(
            mock.patch.object(TAARCacheRedis, "_fetch_ensemble_weights", return_value=DATA, )
        )

        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_whitelist", return_value=WHITELIST_DATA,
            )
        )

        stack = noop_loaders(stack)

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

        # Initialize redis
        cache = TAARCacheRedis.get_instance(ctx)
        cache.safe_load_data()
        ctx[ITAARCache] = cache
        yield stack


def test_weight_cache(test_ctx):
    with mock_install_mock_ensemble_data(test_ctx):
        factory = MockRecommenderFactory()
        test_ctx["recommender_factory"] = factory

        test_ctx["recommender_map"] = {
            "collaborative": factory.create("collaborative"),
            "similarity": factory.create("similarity"),
            "locale": factory.create("locale"),
        }

        r = EnsembleRecommender(test_ctx)
        actual = r.getWeights()
        assert EXPECTED == actual


def test_recommendations(test_ctx):
    with MetricsMock() as mm:
        with mock_install_mock_ensemble_data(test_ctx):
            EXPECTED_RESULTS = [
                ("ghi", 3430.0),
                ("def", 3320.0),
                ("ijk", 3200.0),
                ("hij", 3100.0),
                ("lmn", 420.0),
            ]

            factory = MockRecommenderFactory()
            test_ctx["recommender_factory"] = factory

            test_ctx["recommender_map"] = {
                "collaborative": factory.create("collaborative"),
                "similarity": factory.create("similarity"),
                "locale": factory.create("locale"),
            }
            r = EnsembleRecommender(test_ctx)
            client = {"client_id": "12345"}  # Anything will work here

            recommendation_list = r.recommend(client, 5)
            assert isinstance(recommendation_list, list)
            assert recommendation_list == EXPECTED_RESULTS

            assert mm.has_record(TIMING, "taar.ensemble_recommend")
            assert mm.has_record(TIMING, "taar.collaborative_recommend")
            assert mm.has_record(TIMING, "taar.locale_recommend")
            assert mm.has_record(TIMING, "taar.similarity_recommend")


def test_preinstalled_guids(test_ctx):
    with mock_install_mock_ensemble_data(test_ctx):
        EXPECTED_RESULTS = [
            ("ghi", 3430.0),
            ("ijk", 3200.0),
            ("lmn", 420.0),
            ("klm", 409.99999999999994),
            ("abc", 23.0),
        ]

        factory = MockRecommenderFactory()
        test_ctx["recommender_factory"] = factory

        test_ctx["recommender_map"] = {
            "collaborative": factory.create("collaborative"),
            "similarity": factory.create("similarity"),
            "locale": factory.create("locale"),
        }
        r = EnsembleRecommender(test_ctx)

        # 'hij' should be excluded from the suggestions list
        # The other two addon GUIDs 'def' and 'jkl' will never be
        # recommended anyway and should have no impact on results
        client = {"client_id": "12345", "installed_addons": ["def", "hij", "jkl"]}

        recommendation_list = r.recommend(client, 5)
        print(recommendation_list)
        assert isinstance(recommendation_list, list)
        assert recommendation_list == EXPECTED_RESULTS


def test_mock_client_ids(test_ctx):
    with mock_install_mock_ensemble_data(test_ctx):

        EXPECTED_RESULTS = [
            ("2.0@disconnect.me", 0.17),
            ("@contain-facebook", 0.25),
            ("@testpilot-containers", 0.72),
            ("CookieAutoDelete@kennydo.com", 0.37),
            ("FirefoxColor@mozilla.com", 0.32),
        ]

        factory = MockRecommenderFactory()
        test_ctx["recommender_factory"] = factory

        test_ctx["recommender_map"] = {
            "collaborative": factory.create("collaborative"),
            "similarity": factory.create("similarity"),
            "locale": factory.create("locale"),
        }
        r = EnsembleRecommender(test_ctx)

        # 'hij' should be excluded from the suggestions list
        # The other two addon GUIDs 'def' and 'jkl' will never be
        # recommended anyway and should have no impact on results
        client = {"client_id": "11111"}

        recommendation_list = r.recommend(client, 5)
        assert isinstance(recommendation_list, list)
        assert recommendation_list == EXPECTED_RESULTS
