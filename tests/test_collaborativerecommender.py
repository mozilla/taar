"""
Test cases for the TAAR CollaborativeRecommender
"""

import numpy

from taar.context import Context
from taar.cache import JSONCache, Clock

from taar.recommenders.collaborative_recommender import ADDON_MAPPING_URL
from taar.recommenders.collaborative_recommender import ADDON_MODEL_URL


from taar.recommenders.collaborative_recommender import CollaborativeRecommender
from taar.recommenders.collaborative_recommender import positive_hash

"""
We need to generate a synthetic list of addons and relative weights
for co-occurance.  It's important to note that the
CollaborativeRecommender model expects that addon IDs are hashed using
the Java hash function.
"""

ADDON_SPACE = [{"id": "addon1.id", "name": "addon1.name", "isWebextension": True},
               {"id": "addon2.id", "name": "addon2.name", "isWebextension": True},
               {"id": "addon3.id", "name": "addon3.name", "isWebextension": True},
               {"id": "addon4.id", "name": "addon4.name", "isWebextension": True},
               {"id": "addon5.id", "name": "addon5.name", "isWebextension": True}]

# Load the addons into the FAKE_MAPPING dictionary
FAKE_MAPPING = {}
for addon in ADDON_SPACE:
    java_hash = positive_hash(addon['id'])
    FAKE_MAPPING[str(java_hash)] = addon

# This matrix sets up addon2 as an overweighted recommended addon
FAKE_ADDON_MATRIX = []
for i, addon in enumerate(ADDON_SPACE):
    row = {"id": positive_hash(addon['id']), "features": [0, 0.2, 0.0, 0.1, 0.15]}
    row['features'][i] = 1.0
    FAKE_ADDON_MATRIX.append(row)

"""
FAKE_ADDON_MATRIX = [
    {"id": 1234, "features": [1.0, 0.0, 0.0]},
    {"id": 4567, "features": [0.0, 1.0, 0.0]},
    {"id": 7890, "features": [0.0, 0.0, 1.0]}
]
"""


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
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    return ctx


def activate_responses(ctx):
    """
    Overload the 'real' addon model and mapping URLs responses so that
    we always the fixture data at the top of this test module.
    """
    # responses.add(responses.GET, ADDON_MODEL_URL, json=FAKE_ADDON_MATRIX)
    # responses.add(responses.GET, ADDON_MAPPING_URL, json=FAKE_MAPPING)
    ctx = ctx.child()

    class MockUtils:
        def fetch_json(self, url):
            if url == ADDON_MODEL_URL:
                return FAKE_ADDON_MATRIX
            elif url == ADDON_MAPPING_URL:
                return FAKE_MAPPING

    ctx['utils'] = MockUtils()
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    return ctx


def test_can_recommend():
    ctx = get_mocked_ctx()
    r = CollaborativeRecommender(ctx)

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})

    # Check that we can recommend if we the user has at least an addon.
    assert r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


def get_error_ctx():
    ctx = Context()
    ctx = activate_error_responses(ctx)
    return ctx


def get_mocked_ctx():
    ctx = Context()
    ctx = activate_responses(ctx)
    return ctx


def test_can_recommend_no_model():
    ctx = get_error_ctx()
    r = CollaborativeRecommender(ctx)

    # We should never be able to recommend if something went wrong with the model.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})
    assert not r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


def test_empty_recommendations():
    # Tests that the empty recommender always recommends an empty list
    # of addons if we have no addons
    ctx = get_mocked_ctx()
    r = CollaborativeRecommender(ctx)
    assert not r.can_recommend({})

    # Note that calling recommend() if can_recommend has failed is not
    # defined.


def test_best_recommendation():
    # Make sure the structure of the recommendations is correct and that we
    # recommended the the right addon.
    ctx = get_mocked_ctx()
    r = CollaborativeRecommender(ctx)

    # An non-empty set of addons should give a list of recommendations
    fixture_client_data = {"installed_addons": ["addon4.id"]}
    assert r.can_recommend(fixture_client_data)
    recommendations = r.recommend(fixture_client_data, 1)

    assert isinstance(recommendations, list)
    assert len(recommendations) == 1

    # Verify that addon2 - the most heavy weighted addon was
    # recommended
    result = recommendations[0]
    assert type(result) is tuple
    assert len(result) == 2
    assert result[0] == 'addon2.id'
    assert type(result[1]) is numpy.float64
    assert numpy.isclose(result[1], numpy.float64('0.3225'))


def test_recommendation_weights():
    """
    Weights should be ordered greatest to lowest
    """
    ctx = get_mocked_ctx()
    r = CollaborativeRecommender(ctx)

    # An non-empty set of addons should give a list of recommendations
    fixture_client_data = {"installed_addons": ["addon4.id"]}
    assert r.can_recommend(fixture_client_data)
    recommendations = r.recommend(fixture_client_data, 2)
    assert isinstance(recommendations, list)
    assert len(recommendations) == 2

    # Verify that addon2 - the most heavy weighted addon was
    # recommended
    result = recommendations[0]
    assert type(result) is tuple
    assert len(result) == 2
    assert result[0] == 'addon2.id'
    assert type(result[1]) is numpy.float64
    assert numpy.isclose(result[1], numpy.float64('0.3225'))

    # Verify that addon2 - the most heavy weighted addon was
    # recommended
    result = recommendations[1]
    assert type(result) is tuple
    assert len(result) == 2
    assert result[0] == 'addon5.id'
    assert type(result[1]) is numpy.float64
    assert numpy.isclose(result[1], numpy.float64('0.29'))


def test_recommender_str():
    """Tests that the string representation of the recommender is correct
    """
    # TODO: this test is brittle and should be removed once it is safe
    # to do so
    ctx = get_mocked_ctx()
    r = CollaborativeRecommender(ctx)
    assert str(r) == "CollaborativeRecommender"
