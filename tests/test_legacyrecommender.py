import pytest

from taar.recommenders import LegacyRecommender

FAKE_LEGACY_DATA = {
    "{test_guid_1}": ["test_guid_2", "test_guid_3"],
    "test_guid_4": ["{test_guid_5}"],
    "{test_guid_6}": ["test_guid_7"]
}


@pytest.fixture
def mock_s3_json_downloader(monkeypatch):
    monkeypatch.setattr('taar.recommenders.utils.get_s3_json_content',
                        lambda x, y: FAKE_LEGACY_DATA)


def test_can_recommend(mock_s3_json_downloader):
    r = LegacyRecommender()

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"disabled_addon_ids": []})

    # Check that we can not recommend if no *legacy* addons are detected,
    # but addon is in loaded resource.
    profile_without_legacy = dict(
        client_id="test-client-id",
        disabled_addon_ids=["test_guid_7",
                            "test_guid_8"],
        locale="it-IT"
    )

    assert not r.can_recommend(profile_without_legacy)


def test_recommendations(mock_s3_json_downloader):
    # Test that the legacy recommender returns the correct addons from the json loaded.
    r = LegacyRecommender()

    limit = 10
    profile_with_legacy = dict(
        client_id="test-client-id",
        disabled_addon_ids=["{test_guid_1}",
                            "test_guid_8"],
        locale="it-IT"
    )

    recommendations = r.recommend(profile_with_legacy, limit)

    # Make sure the structure of the recommendations is correct and that we recommended the the right addons.
    assert isinstance(recommendations, list)

    # Make sure that the reported addons are the ones from the fake data.
    assert "test_guid_2" in recommendations
    assert "test_guid_3" in recommendations


def test_recommender_str(mock_s3_json_downloader):
    # Tests that the string representation of the recommender is correct
    r = LegacyRecommender()
    assert str(r) == "LegacyRecommender"
