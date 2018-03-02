from taar.context import Context
from taar.cache import JSONCache, Clock

from taar.recommenders import LocaleRecommender


FAKE_LOCALE_DATA = {
    "te-ST": [
        "{1e6b8bce-7dc8-481c-9f19-123e41332b72}", "some-other@nice-addon.com",
        "{66d1eed2-a390-47cd-8215-016e9fa9cc55}", "{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}"
    ],
    "en": [
        "some-uuid@test-addon.com", "other-addon@some-id.it"
    ]
}


class MockUtils:
    def get_s3_json_content(self, *args, **kwargs):
        return FAKE_LOCALE_DATA


def create_test_ctx():
    ctx = Context()
    ctx['utils'] = MockUtils()
    ctx['clock'] = Clock()
    ctx['cache'] = JSONCache(ctx)
    return ctx.child()


def test_can_recommend():
    ctx = create_test_ctx()
    r = LocaleRecommender(ctx)

    # Test that we can't recommend if we have not enough client info.
    assert not r.can_recommend({})
    assert not r.can_recommend({"locale": []})

    # Check that we can recommend if the user has at least an addon.
    assert r.can_recommend({"locale": "en"})


def test_can_recommend_no_model():
    ctx = create_test_ctx()
    r = LocaleRecommender(ctx)

    # We should never be able to recommend if something went
    # wrong with the model.
    assert not r.can_recommend({})
    assert not r.can_recommend({"locale": []})
    assert not r.can_recommend({"locale": "it"})


def test_recommendations():
    """Test that the locale recommender returns the correct
    locale dependent addons.

    The JSON output for this recommender should be a list of 2-tuples
    of (GUID, weight).
    """
    ctx = create_test_ctx()
    r = LocaleRecommender(ctx)
    recommendations = r.recommend({"locale": "en"}, 10)

    # Make sure the structure of the recommendations is correct and that we
    # recommended the the right addon.
    assert isinstance(recommendations, list)
    assert len(recommendations) == len(FAKE_LOCALE_DATA["en"])

    # Make sure that the reported addons are the one from the fake data.
    for (addon_id, weight) in recommendations:
        assert 1 == weight
        assert addon_id in FAKE_LOCALE_DATA["en"]


def test_recommender_str():
    """Tests that the string representation of the recommender is correct
    """
    # TODO: this test is brittle and should be removed once it is safe
    # to do so
    ctx = create_test_ctx()
    r = LocaleRecommender(ctx)
    assert str(r) == "LocaleRecommender"


def test_recommender_extra_data():
    # Test that the recommender uses locale data from the "extra"
    # section if available.
    def validate_recommendations(data, expected_locale):
        # Make sure the structure of the recommendations is correct and that we
        # recommended the the right addon.
        assert isinstance(data, list)
        assert len(data) == len(FAKE_LOCALE_DATA[expected_locale])

        # Make sure that the reported addons are the one from the fake data.
        for (addon_id, weight) in data:
            assert addon_id in FAKE_LOCALE_DATA[expected_locale]
            assert 1 == weight

    ctx = create_test_ctx()
    r = LocaleRecommender(ctx)
    recommendations = r.recommend({}, 10, extra_data={"locale": "en"})
    validate_recommendations(recommendations, "en")

    # Make sure that we favour client data over the extra data.
    recommendations = r.recommend({"locale": "en"}, 10, extra_data={"locale": "te-ST"})
    validate_recommendations(recommendations, "en")
