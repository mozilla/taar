import pytest

from taar.recommenders import LegacyRecommender

FAKE_LEGACY_DATA = {
    "guid-01":
        ["guid-02", 'guid-11-4'],
    "guid-03":
        ["guid-05", 'guid-16-4'],
    "guid-05":
        ["guid-06", 'guid-20-8'],
    "guid-07": ["guid-08-1", "guid-09-2", "guid-10-3"],
    "guid-12": ["guid-13-1", "guid-14-2", "guid-15-3",
                "guid-17-5", "guid-18-6", "guid-19-7",
                "guid-21-9", "guid-22-10"],
    "guid-23": []
}

LIMIT = 10


@pytest.fixture
def mock_s3_json_downloader(monkeypatch):
    monkeypatch.setattr('taar.recommenders.utils.get_s3_json_content',
                        lambda x, y: FAKE_LEGACY_DATA)


def test_can_recommend(mock_s3_json_downloader):
    r = LegacyRecommender()

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"disabled_addons_ids": []})

    # Check that we can not recommend if no *legacy* addons are detected,
    # but addon is in loaded resource.
    profile_without_legacy = dict(
        client_id="test-client-id",
        disabled_addons_ids=["test_guid_7",
                             "test_guid_8"],
        locale="it-IT"
    )

    assert not r.can_recommend(profile_without_legacy)


def test_recommendations(mock_s3_json_downloader):
    """Test that the legacy recommender returns the correct addons from the json loaded.

    The JSON output for this recommender should be a list of 2-tuples
    of (GUID, weight).
    """
    r = LegacyRecommender()

    profile_with_many_legacy = dict(
        client_id="test-client-id",
        disabled_addons_ids=["guid-01",
                             "guid-05",
                             "guid-12"],
        locale="it-IT"
    )

    recommendations = r.recommend(profile_with_many_legacy, LIMIT)

    assert len(recommendations) == LIMIT
    assert ("guid-13-1", 1) in recommendations
    assert ("guid-21-9", 1) not in recommendations
    assert ("guid-22-10", 1) not in recommendations
    assert ("guid-21-9", 1) not in recommendations


def test_recommender_str(mock_s3_json_downloader):
    """Tests that the string representation of the recommender is correct
    """
    # TODO: this test is brittle and should be removed once it is safe
    # to do so
    r = LegacyRecommender()
    assert str(r) == "LegacyRecommender"
