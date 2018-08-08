# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Test cases for the TAAR Hybrid recommender
"""

from taar.recommenders.hybrid_recommender import CuratedRecommender

from taar.recommenders.hybrid_recommender import S3_BUCKET
from taar.recommenders.hybrid_recommender import CURATED_WHITELIST
# from taar.recommenders.hybrid_recommender import ENSEMBLE_WEIGHTS
from taar.recommenders.lazys3 import LazyJSONLoader

import json
from moto import mock_s3
import boto3

import pytest


def install_no_curated_data(ctx):
    ctx = ctx.child()
    conn = boto3.resource('s3', region_name='us-west-2')

    conn.create_bucket(Bucket=S3_BUCKET)
    conn.Object(S3_BUCKET, CURATED_WHITELIST).put(Body="")
    ctx['curated_whitelist_data'] = LazyJSONLoader(ctx,
                                                   S3_BUCKET,
                                                   CURATED_WHITELIST)

    return ctx


def install_mock_curated_data(ctx):
    mock_data = []
    for i in range(20):
        mock_data.append({'GUID': str(i) * 16,
                          'Extension': 'WebExt %d' % i,
                          'Copy (final)': 'Copy for %d' % i})

    ctx = ctx.child()
    conn = boto3.resource('s3', region_name='us-west-2')

    conn.create_bucket(Bucket=S3_BUCKET)
    conn.Object(S3_BUCKET, CURATED_WHITELIST).put(Body=json.dumps(mock_data))
    ctx['curated_whitelist_data'] = LazyJSONLoader(ctx,
                                                   S3_BUCKET,
                                                   CURATED_WHITELIST)

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
        guid_list = r.recommend({'client_id': '000000'}, limit = LIMIT)
        # The curated recommendations should always return with some kind
        # of recommendations
        assert len(guid_list) == LIMIT


@pytest.mark.skip("TODO")
def test_hybrid_recommendations(test_ctx):
    pass
