import pytest
import responses

from taar.recommenders.collaborative_recommender import CollaborativeRecommender, ADDON_MODEL_URL, ADDON_MAPPING_URL


FAKE_MAPPING = {
    "1234": "Nice addon name",
    "4567": "Better than the previous one",
    "7890": "Super"
}
FAKE_ADDON_MATRIX = [
    {"id": "1234", "features": [1.0, 0.0, 0.0]},
    {"id": "4567", "features": [0.0, 1.0, 0.0]},
    {"id": "7890", "features": [0.0, 0.0, 1.0]}
]


@pytest.fixture
def activate_error_responses():
    responses.add(responses.GET, ADDON_MODEL_URL, json={"error": "not found"}, status=404)
    responses.add(responses.GET, ADDON_MAPPING_URL, json={"error": "not found"}, status=404)


@pytest.fixture
def activate_responses():
    responses.add(responses.GET, ADDON_MODEL_URL, json=FAKE_ADDON_MATRIX)
    responses.add(responses.GET, ADDON_MAPPING_URL, json=FAKE_MAPPING)


@responses.activate
def test_can_recommend(activate_responses):
    r = CollaborativeRecommender()

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})

    # Check that we can recommend if we the user has at least an addon.
    assert r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


@responses.activate
def test_can_recommend_no_model(activate_error_responses):
    r = CollaborativeRecommender()

    # We should never be able to recommend if something went wrong with the model.
    assert not r.can_recommend({})
    assert not r.can_recommend({"installed_addons": []})
    assert not r.can_recommend({"installed_addons": ["uBlock0@raymondhill.net"]})


@responses.activate
def test_recommendations(activate_responses):
    # Tests that the empty recommender always recommends an empty list
    # of addons.
    r = CollaborativeRecommender()
    recommendations = r.recommend({}, 1)

    # Make sure the structure of the recommendations is correct and that we
    # recommended the the right addon.
    assert isinstance(recommendations, list)
    assert len(recommendations) == 1


# TODO: add test coverage for errors fetching HTTP files.
