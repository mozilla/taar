# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Test cases for the TAAR Hybrid recommender
"""

from taar.recommenders.hybrid_recommender import CuratedRecommender
from taar.recommenders.hybrid_recommender import HybridRecommender
from taar.recommenders.ensemble_recommender import EnsembleRecommender

from taar.recommenders.s3config import TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY

# from taar.recommenders.hybrid_recommender import ENSEMBLE_WEIGHTS
from .test_ensemblerecommender import install_mock_ensemble_data
from .mocks import MockRecommenderFactory

import json
from moto import mock_s3
import boto3


def install_no_curated_data(ctx):
    conn = boto3.resource("s3", region_name="us-west-2")

    conn.create_bucket(Bucket=TAAR_WHITELIST_BUCKET)
    conn.Object(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY).put(Body="")

    return ctx


def install_mock_curated_data(ctx):
    mock_data = []
    for i in range(20):
        mock_data.append(str(i) * 16)

    conn = boto3.resource("s3", region_name="us-west-2")

    conn.create_bucket(Bucket=TAAR_WHITELIST_BUCKET)
    conn.Object(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY).put(
        Body=json.dumps(mock_data)
    )

    return ctx


def install_ensemble_fixtures(ctx):
    ctx = install_mock_ensemble_data(ctx)

    factory = MockRecommenderFactory()
    ctx.set("recommender_factory", factory)

    ctx.set(
        "recommender_map",
        {
            "collaborative": factory.create("collaborative"),
            "similarity": factory.create("similarity"),
            "locale": factory.create("locale"),
        },
    )
    ctx.set("ensemble_recommender", EnsembleRecommender(ctx))
    return ctx


@mock_s3
def test_curated_can_recommend(test_ctx):
    ctx = install_no_curated_data(test_ctx)
    r = CuratedRecommender(ctx)

    # CuratedRecommender will always recommend something no matter
    # what
    assert r.can_recommend({})
    assert r.can_recommend({"installed_addons": []})


@mock_s3
def test_curated_recommendations(test_ctx):
    ctx = install_mock_curated_data(test_ctx)
    r = CuratedRecommender(ctx)

    # CuratedRecommender will always recommend something no matter
    # what

    for LIMIT in range(1, 5):
        guid_list = r.recommend({"client_id": "000000"}, limit=LIMIT)
        # The curated recommendations should always return with some kind
        # of recommendations
        assert len(guid_list) == LIMIT


@mock_s3
def test_hybrid_recommendations(test_ctx):
    # verify that the recommendations mix the curated and
    # ensemble results
    ctx = install_mock_curated_data(test_ctx)
    ctx = install_ensemble_fixtures(ctx)

    r = HybridRecommender(ctx)

    # Test that we can generate lists of results
    for LIMIT in range(4, 8):
        guid_list = r.recommend({"client_id": "000000"}, limit=LIMIT)
        # The curated recommendations should always return with some kind
        # of recommendations
        assert len(guid_list) == LIMIT

    # Test that the results are actually mixed
    guid_list = r.recommend({"client_id": "000000"}, limit=4)

    # A mixed list will have two recommendations with weight > 1.0
    # (ensemble) and 2 with exactly weight 1.0 from the curated list

    assert guid_list[0][1] > 1.0
    assert guid_list[1][1] > 1.0
    assert guid_list[2][1] == 1.0
    assert guid_list[3][1] == 1.0
