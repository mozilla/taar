# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import mock

import contextlib
import fakeredis
from taar.recommenders.redis_cache import AddonsCoinstallCache

import json


from taar.recommenders import LocaleRecommender
from taar.settings import TAAR_LOCALE_KEY, TAAR_LOCALE_BUCKET

from markus import TIMING
from markus.testing import MetricsMock


FAKE_LOCALE_DATA = {
    "te-ST": [
        ["{1e6b8bce-7dc8-481c-9f19-123e41332b72}", 0.1],
        ["some-other@nice-addon.com", 0.2],
        ["{66d1eed2-a390-47cd-8215-016e9fa9cc55}", 0.3],
        ["{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}", 0.4],
    ],
    "en": [["other-addon@some-id.it", 0.3], ["some-uuid@test-addon.com", 0.1]],
}


def install_mock_data(ctx):
    ctx = ctx.child()
    conn = boto3.resource("s3", region_name="us-west-2")

    conn.create_bucket(Bucket=TAAR_LOCALE_BUCKET)
    conn.Object(TAAR_LOCALE_BUCKET, TAAR_LOCALE_KEY).put(
        Body=json.dumps(FAKE_LOCALE_DATA)
    )

    return ctx


def noop_taarlite_dataload(stack):
    # no-op the taarlite rankdata
    stack.enter_context(
        mock.patch.object(AddonsCoinstallCache, "_update_rank_data", return_value=None)
    )
    # no-op the taarlite guidguid data
    stack.enter_context(
        mock.patch.object(
            AddonsCoinstallCache, "_update_coinstall_data", return_value=None,
        )
    )
    return stack


@contextlib.contextmanager
def mock_locale_data(ctx):
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            mock.patch.object(
                AddonsCoinstallCache,
                "_fetch_locale_data",
                return_value=FAKE_LOCALE_DATA,
            )
        )

        stack = noop_taarlite_dataload(stack)

        # Patch fakeredis in
        stack.enter_context(
            mock.patch.object(
                AddonsCoinstallCache,
                "init_redis_connections",
                return_value={
                    0: fakeredis.FakeStrictRedis(db=0),
                    1: fakeredis.FakeStrictRedis(db=1),
                    2: fakeredis.FakeStrictRedis(db=2),
                },
            )
        )

        # Initialize redis
        AddonsCoinstallCache(ctx).safe_load_data()
        yield stack


def test_can_recommend(test_ctx):
    with mock_locale_data(test_ctx):
        r = LocaleRecommender(test_ctx)

        # Test that we can't recommend if we have not enough client info.
        assert not r.can_recommend({})
        assert not r.can_recommend({"locale": []})

        # Check that we can recommend if the user has at least an addon.
        assert r.can_recommend({"locale": "en"})


def test_can_recommend_no_model(test_ctx):
    with mock_locale_data(test_ctx):
        r = LocaleRecommender(test_ctx)

        # We should never be able to recommend if something went
        # wrong with the model.
        assert not r.can_recommend({})
        assert not r.can_recommend({"locale": []})
        assert not r.can_recommend({"locale": "it"})


def test_recommendations(test_ctx):
    """Test that the locale recommender returns the correct
    locale dependent addons.

    The JSON output for this recommender should be a list of 2-tuples
    of (GUID, weight).
    """
    with MetricsMock() as mm:
        with mock_locale_data(test_ctx):
            r = LocaleRecommender(test_ctx)

            recommendations = r.recommend({"locale": "en"}, 10)

            # Make sure the structure of the recommendations is correct and that we
            # recommended the the right addon.
            assert isinstance(recommendations, list)
            assert len(recommendations) == len(FAKE_LOCALE_DATA["en"])

            # Make sure that the reported addons are the one from the fake data.
            for (addon_id, weight), (expected_id, expected_weight) in zip(
                recommendations, FAKE_LOCALE_DATA["en"]
            ):
                assert addon_id == expected_id
                assert weight == expected_weight

            assert mm.has_record(TIMING, "taar.locale_recommend")


def test_recommender_extra_data(test_ctx):
    # Test that the recommender uses locale data from the "extra"
    # section if available.
    def validate_recommendations(data, expected_locale):
        # Make sure the structure of the recommendations is correct and that we
        # recommended the the right addon.
        data = sorted(data, key=lambda x: x[1], reverse=True)
        assert isinstance(data, list)
        assert len(data) == len(FAKE_LOCALE_DATA[expected_locale])

        # Make sure that the reported addons are the one from the fake data.
        for (addon_id, weight), (expected_id, expected_weight) in zip(
            data, FAKE_LOCALE_DATA[expected_locale]
        ):
            assert addon_id == expected_id
            assert weight == expected_weight

    with mock_locale_data(test_ctx):
        r = LocaleRecommender(test_ctx)
        recommendations = r.recommend({}, 10, extra_data={"locale": "en"})
        validate_recommendations(recommendations, "en")

        # Make sure that we favour client data over the extra data.
        recommendations = r.recommend(
            {"locale": "en"}, 10, extra_data={"locale": "te-ST"}
        )
        validate_recommendations(recommendations, "en")
