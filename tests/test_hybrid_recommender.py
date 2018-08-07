# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Test cases for the TAAR Hybrid recommender
"""

from taar.recommenders.hybrid_recommender import CuratedRecommender
from taar.recommenders.hybrid_recommender import HybridRecommender

import pytest


def activate_error_responses(ctx):
    """
    Overload the 'real' addon model and mapping URLs responses so that
    we always get 404 errors.
    """
    ctx = ctx.child()

    class ErrorUtils:
        def fetch_json(self, url):
            return None
    ctx['utils'] = ErrorUtils()
    return ctx


def test_curated_can_recommend(test_ctx):
    ctx = test_ctx
    r = CuratedRecommender(ctx)

    # CuratedRecommender will always recommend something no matter
    # what
    assert r.can_recommend({})
    assert r.can_recommend({"installed_addons": []})


# These should fail because of s3 data loaders
@pytest.mark.xfail
def test_curated_recommendations(test_ctx):
    ctx = test_ctx
    r = CuratedRecommender(ctx)

    # CuratedRecommender will always recommend something no matter
    # what

    for LIMIT in range(1, 5):
        guid_list = r.recommend({'client_id': '000000'}, limit = LIMIT)
        # The curated recommendations should always return with some kind
        # of recommendations
        assert len(guid_list) == LIMIT
