# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Test cases for the TAAR CollaborativeRecommender
"""

import contextlib

import fakeredis
import mock
import numpy

from taar.interfaces import ITAARCache
from taar.recommenders.collaborative_recommender import CollaborativeRecommender
from taar.recommenders.collaborative_recommender import positive_hash
from taar.recommenders.redis_cache import TAARCacheRedis
from .noop_fixtures import (
    noop_taarlocale_dataload,
    noop_taarlite_dataload,
    noop_taarensemble_dataload,
    noop_taarsimilarity_dataload,
)

"""
We need to generate a synthetic list of addons and relative weights
for co-occurance.  It's important to note that the
CollaborativeRecommender model expects that addon IDs are hashed using
the Java hash function.
"""


def noop_other_recommenders(stack):
    stack = noop_taarlocale_dataload(stack)
    stack = noop_taarlite_dataload(stack)
    stack = noop_taarsimilarity_dataload(stack)
    stack = noop_taarensemble_dataload(stack)
    return stack


@contextlib.contextmanager
def mock_install_none_mock_data(ctx):
    """
    Overload the 'real' addon model and mapping URLs responses so that
    we always get 404 errors.
    """
    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None

        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_collaborative_item_matrix", return_value="",
            )
        )
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_collaborative_mapping_data", return_value="",
            )
        )

        stack = noop_other_recommenders(stack)

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


@contextlib.contextmanager
def mock_install_mock_data(ctx):
    addon_space = [
        {"id": "addon1.id", "name": "addon1.name", "isWebextension": True},
        {"id": "addon2.id", "name": "addon2.name", "isWebextension": True},
        {"id": "addon3.id", "name": "addon3.name", "isWebextension": True},
        {"id": "addon4.id", "name": "addon4.name", "isWebextension": True},
        {"id": "addon5.id", "name": "addon5.name", "isWebextension": True},
    ]

    fake_addon_matrix = []
    for i, addon in enumerate(addon_space):
        row = {
            "id": positive_hash(addon["id"]),
            "features": [0, 0.2, 0.0, 0.1, 0.15],
        }
        row["features"][i] = 1.0
        fake_addon_matrix.append(row)

    fake_mapping = {}
    for addon in addon_space:
        java_hash = positive_hash(addon["id"])
        fake_mapping[str(java_hash)] = addon

    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "_fetch_collaborative_item_matrix",
                return_value=fake_addon_matrix,
            )
        )
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "_fetch_collaborative_mapping_data",
                return_value=fake_mapping,
            )
        )

        stack = noop_other_recommenders(stack)

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


def test_cant_recommend(test_ctx):
    with mock_install_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)

        # Test that we can't recommend if we have not enough client info.
        assert not r.can_recommend({})
        assert not r.can_recommend({"installed_addons": []})


def test_can_recommend(test_ctx):
    with mock_install_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)

        # Check that we can recommend if the user has at least an addon.
        assert r.can_recommend(
            {
                "installed_addons": ["uBlock0@raymondhill.net"],
                "client_id": "test-client",
            }
        )


def test_can_recommend_no_model(test_ctx):
    with mock_install_none_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)

        # We should never be able to recommend if something went wrong with the model.
        assert not r.can_recommend({})
        assert not r.can_recommend({"installed_addons": []})
        assert not r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


def test_empty_recommendations(test_ctx):
    # Tests that the empty recommender always recommends an empty list
    # of addons if we have no addons
    with mock_install_none_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)
        assert not r.can_recommend({})

        # Note that calling recommend() if can_recommend has failed is not
        # defined.


def test_best_recommendation(test_ctx):
    # Make sure the structure of the recommendations is correct and that we
    # recommended the the right addon.
    with mock_install_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)

        # An non-empty set of addons should give a list of recommendations
        fixture_client_data = {
            "installed_addons": ["addon4.id"],
            "client_id": "test_client",
        }
        assert r.can_recommend(fixture_client_data)
        recommendations = r.recommend(fixture_client_data, 1)

        assert isinstance(recommendations, list)
        assert len(recommendations) == 1

        # Verify that addon2 - the most heavy weighted addon was
        # recommended
        result = recommendations[0]
        assert type(result) is tuple
        assert len(result) == 2
        assert result[0] == "addon2.id"
        assert type(result[1]) is numpy.float64
        assert numpy.isclose(result[1], numpy.float64("0.3225"))


def test_recommendation_weights(test_ctx):
    """
    Weights should be ordered greatest to lowest
    """
    with mock_install_mock_data(test_ctx):
        r = CollaborativeRecommender(test_ctx)

        # An non-empty set of addons should give a list of recommendations
        fixture_client_data = {
            "installed_addons": ["addon4.id"],
            "client_id": "test_client",
        }
        assert r.can_recommend(fixture_client_data)
        recommendations = r.recommend(fixture_client_data, 2)
        assert isinstance(recommendations, list)
        assert len(recommendations) == 2

        # Verify that addon2 - the most heavy weighted addon was
        # recommended
        result = recommendations[0]
        assert type(result) is tuple
        assert len(result) == 2
        assert result[0] == "addon2.id"
        assert type(result[1]) is numpy.float64
        assert numpy.isclose(result[1], numpy.float64("0.3225"))

        # Verify that addon2 - the most heavy weighted addon was
        # recommended
        result = recommendations[1]
        assert type(result) is tuple
        assert len(result) == 2
        assert result[0] == "addon5.id"
        assert type(result[1]) is numpy.float64
        assert numpy.isclose(result[1], numpy.float64("0.29"))
