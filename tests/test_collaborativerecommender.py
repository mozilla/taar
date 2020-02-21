# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Test cases for the TAAR CollaborativeRecommender
"""

import numpy

from moto import mock_s3
import boto3
import pickle
from taar.recommenders.collaborative_recommender import (
    TAAR_ITEM_MATRIX_BUCKET,
    TAAR_ITEM_MATRIX_KEY,
    TAAR_ADDON_MAPPING_BUCKET,
    TAAR_ADDON_MAPPING_KEY,
)

from taar.recommenders.collaborative_recommender import CollaborativeRecommender
from taar.recommenders.collaborative_recommender import positive_hash
import json


"""
We need to generate a synthetic list of addons and relative weights
for co-occurance.  It's important to note that the
CollaborativeRecommender model expects that addon IDs are hashed using
the Java hash function.
"""


def install_none_mock_data(ctx):
    """
    Overload the 'real' addon model and mapping URLs responses so that
    we always get 404 errors.
    """
    conn = boto3.resource("s3", region_name="us-west-2")

    conn.create_bucket(Bucket=TAAR_ITEM_MATRIX_BUCKET)
    conn.Object(TAAR_ITEM_MATRIX_BUCKET, TAAR_ITEM_MATRIX_KEY).put(Body="")

    # Don't reuse connections with moto.  badness happens
    conn = boto3.resource("s3", region_name="us-west-2")
    conn.create_bucket(Bucket=TAAR_ADDON_MAPPING_BUCKET)
    conn.Object(TAAR_ADDON_MAPPING_BUCKET, TAAR_ADDON_MAPPING_KEY).put(Body="")
    return ctx


def install_mock_data(ctx):
    """
    Overload the 'real' addon model and mapping URLs responses so that
    we always the fixture data at the top of this test module.
    """

    addon_space = [
        {"id": "addon1.id", "name": "addon1.name", "isWebextension": True},
        {"id": "addon2.id", "name": "addon2.name", "isWebextension": True},
        {"id": "addon3.id", "name": "addon3.name", "isWebextension": True},
        {"id": "addon4.id", "name": "addon4.name", "isWebextension": True},
        {"id": "addon5.id", "name": "addon5.name", "isWebextension": True},
    ]

    fake_addon_matrix = []
    for i, addon in enumerate(addon_space):
        row = {"id": positive_hash(addon["id"]), "features": [0, 0.2, 0.0, 0.1, 0.15]}
        row["features"][i] = 1.0
        fake_addon_matrix.append(row)

    fake_mapping = {}
    for addon in addon_space:
        java_hash = positive_hash(addon["id"])
        fake_mapping[str(java_hash)] = addon

    conn = boto3.resource("s3", region_name="us-west-2")
    conn.create_bucket(Bucket=TAAR_ITEM_MATRIX_BUCKET)
    conn.Object(TAAR_ITEM_MATRIX_BUCKET, TAAR_ITEM_MATRIX_KEY).put(
        Body=json.dumps(fake_addon_matrix)
    )

    conn = boto3.resource("s3", region_name="us-west-2")
    conn.create_bucket(Bucket=TAAR_ADDON_MAPPING_BUCKET)
    conn.Object(TAAR_ADDON_MAPPING_BUCKET, TAAR_ADDON_MAPPING_KEY).put(
        Body=json.dumps(fake_mapping)
    )

    return ctx


@mock_s3
def test_cant_recommend(test_ctx):
    ctx = install_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})

@mock_s3
def test_can_pickle(test_ctx):
    ctx = install_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

    r_pickle = pickle.dumps(r)
    r2 = pickle.loads(r_pickle)


@mock_s3
def test_can_recommend(test_ctx):
    ctx = install_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

    # For some reason, moto doesn't like to play nice with this call
    # Check that we can recommend if we the user has at least an addon.
    assert r.can_recommend(
        {"installed_addons": ["uBlock0@raymondhill.net"], "client_id": "test-client"}
    )


@mock_s3
def test_can_recommend_no_model(test_ctx):
    ctx = install_none_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

    # We should never be able to recommend if something went wrong with the model.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})
    assert not r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


@mock_s3
def test_empty_recommendations(test_ctx):
    # Tests that the empty recommender always recommends an empty list
    # of addons if we have no addons
    ctx = install_none_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)
    assert not r.can_recommend({})

    # Note that calling recommend() if can_recommend has failed is not
    # defined.


@mock_s3
def test_best_recommendation(test_ctx):
    # Make sure the structure of the recommendations is correct and that we
    # recommended the the right addon.
    ctx = install_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

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


@mock_s3
def test_recommendation_weights(test_ctx):
    """
    Weights should be ordered greatest to lowest
    """
    ctx = install_mock_data(test_ctx)
    r = CollaborativeRecommender(ctx)

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
