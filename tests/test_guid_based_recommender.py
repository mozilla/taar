import json

import fakeredis
import pytest
import mock
import contextlib

from taar.interfaces import ITAARCache
from .noop_fixtures import (
    noop_taarlocale_dataload,
    noop_taarcollab_dataload,
    noop_taarsimilarity_dataload,
    noop_taarensemble_dataload,
)

from taar.recommenders.guid_based_recommender import GuidBasedRecommender
from taar.recommenders.redis_cache import TAARCacheRedis

from taar.recommenders.cache import NORMDATA_GUID_ROW_NORM_PREFIX

from taar.recommenders.ua_parser import parse_ua, OSNAME_TO_ID

from markus import TIMING
from markus.testing import MetricsMock

# The different kinds of results we can expect from TAARlite are
# listed below.  Note that the ordering of GUIDs returned, and even
# the set of GUIDs returned may be altered by the different weight
# normalization modes.
#
# Based on some preliminary clustering analysis, the 'rownorm_sum'
# method appears to provide qualitatively better results than the
# other normalization modes including no normalization.


# Reading the RESULTS is not entirely obvious.  The recommendation
# list consists of 2-tuples containing a guid, followed by a lexically
# sorted weight+install count.
# The weights are formatted as a fixed with zero padded float, with
# an addition suffix of a decimal and a zero padded instllation count
# for the addon.
#
# The clearest example of this is the 'rownorm_sum_tiebreak' results
# where each of the computed weights are the same (0.25), but the
# installation count varies.
RESULTS = {
    "default": [
        ("guid-2", "000001000.0000000000.0000000009"),
        ("guid-3", "000000100.0000000000.0000000008"),
        ("guid-4", "000000010.0000000000.0000000007"),
        ("guid-5", "000000001.0000000000.0000000006"),
    ],
    "row_count": [
        ("guid-3", "000000020.0000000000.0000000008"),  # 50% of 40
        ("guid-1", "000000016.6666666667.0000000010"),  # 1/3 of 50
        ("guid-8", "000000015.0000000000.0000000003"),  # 50% of 30
        ("guid-4", "000000006.6666666667.0000000007"),
    ],  # 1/3 of 20
    "rownorm_sum": [
        ("guid-3", "000000000.7478143914.0000000008"),
        ("guid-1", "000000000.4035916824.0000000010"),
        ("guid-8", "000000000.3788819876.0000000003"),
        ("guid-4", "000000000.2803125788.0000000007"),
    ],
    "rownorm_sum_tiebreak": [
        ("guid-1", "000000000.2500000000.0000000010"),
        ("guid-3", "000000000.2500000000.0000000008"),
        ("guid-4", "000000000.2500000000.0000000007"),
        ("guid-5", "000000000.2500000000.0000000006"),
    ],
    "rownorm_sum_tiebreak_cutoff": [
        ("guid-1", "000000000.3333333333.0000010000"),  # noqa
        ("guid-3", "000000000.3333333333.0000008000"),  # noqa
        ("guid-5", "000000000.3333333333.0000006000"),
    ],  # noqa
    "row_sum": [
        ("guid-1", "000000000.3225806452.0000000010"),
        ("guid-3", "000000000.2857142857.0000000008"),
        ("guid-8", "000000000.2307692308.0000000003"),
        ("guid-4", "000000000.2000000000.0000000007"),
    ],
    "guidception": [
        ("guid-1", "000000000.2666666667.0000000010"),
        ("guid-3", "000000000.2333333333.0000000008"),
        ("guid-8", "000000000.2000000000.0000000003"),
        ("guid-4", "000000000.1666666667.0000000007"),
    ],
}


@contextlib.contextmanager
def mock_coinstall_ranking_context(ctx, mock_coinstall, mock_ranking):

    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None

        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_ranking_data", return_value=mock_ranking,
            )
        )
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_coinstall_data", return_value=mock_coinstall,
            )
        )

        stack = noop_taarlocale_dataload(stack)
        stack = noop_taarcollab_dataload(stack)
        stack = noop_taarsimilarity_dataload(stack)
        stack = noop_taarensemble_dataload(stack)

        # Patch fakeredis in
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "init_redis_connections",
                return_value={
                    0: fakeredis.FakeStrictRedis(db=0),
                    1: fakeredis.FakeStrictRedis(db=1),
                    2: fakeredis.FakeStrictRedis(db=2),
                },
            )
        )

        # Initialize redis
        cache = TAARCacheRedis.get_instance(ctx)
        cache.safe_load_data()
        ctx[ITAARCache] = cache
        yield stack


def test_recommender_nonormal(test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):
        with MetricsMock() as mm:
            EXPECTED_RESULTS = RESULTS["default"]
            recommender = GuidBasedRecommender(test_ctx)

            guid = "guid-1"

            actual = recommender.recommend({"guid": guid, "normalize": "none"})
            assert actual == EXPECTED_RESULTS

            mm.has_record(TIMING, "taar.guid_coinstall")
            mm.has_record(TIMING, "taar.guid_ranking")
            mm.has_record(TIMING, "taar.guid_recommendation")


def test_row_count_recommender(
    test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):

        EXPECTED_RESULTS = RESULTS["row_count"]

        recommender = GuidBasedRecommender(test_ctx)
        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "row_count"})

        # Note that guid-9 is not included because it's weight is
        # decreased 50% to 5
        assert EXPECTED_RESULTS == actual


def test_rownorm_sumrownorm(test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):
        EXPECTED_RESULTS = RESULTS["rownorm_sum"]
        recommender = GuidBasedRecommender(test_ctx)
        guid = "guid-2"

        default_actual = recommender.recommend({"guid": guid})

        actual = recommender.recommend({"guid": guid, "normalize": "rownorm_sum"})

        # Default normalization is rownorm_sum
        assert actual == default_actual
        assert actual == EXPECTED_RESULTS
        """
        Some notes on verifying guid-1:

        Numerator is the row weighted value of guid-1 : 50/150
        Denominator is the sum of the row weighted value of guid-1 in all
        other rows

        (guid-2) 50/150
        (guid-3) 100/210
        (guid-6) 5/305

        This gives us: [0.3333333333333333,
                        0.47619047619047616,
                        0.01639344262295082]

        so the final result should be (5/150) / (50/150 + 100/210 + 5/305)

        That gives a final expected weight for guid-1 to be: 0.403591682
        """
        expected = 0.403591682
        actual = float(actual[1][1][:-11])
        assert expected == pytest.approx(actual, rel=1e-3)


def test_rowsum_recommender(test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):
        EXPECTED_RESULTS = RESULTS["row_sum"]

        recommender = GuidBasedRecommender(test_ctx)
        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "row_sum"})
        assert 4 == len(actual)

        expected_val = 50 / 155
        actual_val = float(actual[0][1][:-11])
        assert expected_val == pytest.approx(actual_val, rel=1e-3)

        assert actual == EXPECTED_RESULTS


def test_guidception(test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):

        EXPECTED_RESULTS = RESULTS["guidception"]

        recommender = GuidBasedRecommender(test_ctx)
        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "guidception"})
        assert actual == EXPECTED_RESULTS


def test_rownorm_sum_tiebreak(
    test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):
        EXPECTED_RESULTS = RESULTS["rownorm_sum_tiebreak"]

        recommender = GuidBasedRecommender(test_ctx)
        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "rownorm_sum"})

        # Note that the results have weights that are equal, but the tie
        # break is solved by the install rate.
        assert actual == EXPECTED_RESULTS


def test_missing_rownorm_data_issue_31(
    test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):

        recommender = GuidBasedRecommender(test_ctx)

        EXPECTED_RESULTS = RESULTS["rownorm_sum_tiebreak"]

        # Explicitly destroy the guid-4 key in the row_norm data
        recommender._cache._db().delete(NORMDATA_GUID_ROW_NORM_PREFIX + "guid-4")
        for i, row in enumerate(EXPECTED_RESULTS):
            if row[0] == "guid-4":
                del EXPECTED_RESULTS[i]
                break

        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "rownorm_sum"})

        assert actual == EXPECTED_RESULTS


def test_divide_by_zero_rownorm_data_issue_31(
    test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
):
    with mock_coinstall_ranking_context(
        test_ctx, TAARLITE_TIE_MOCK_DATA, TAARLITE_MOCK_GUID_RANKING
    ):

        recommender = GuidBasedRecommender(test_ctx)

        EXPECTED_RESULTS = RESULTS["rownorm_sum_tiebreak"]

        # Explicitly set the guid-4 key in the row_norm data to have a sum
        # of zero weights
        recommender._cache._db().set(
            NORMDATA_GUID_ROW_NORM_PREFIX + "guid-4", json.dumps([0, 0, 0])
        )

        # Destroy the guid-4 key in the expected results as a sum of 0
        # will generate a divide by zero error
        for i, row in enumerate(EXPECTED_RESULTS):
            if row[0] == "guid-4":
                del EXPECTED_RESULTS[i]
                break

        guid = "guid-2"

        actual = recommender.recommend({"guid": guid, "normalize": "rownorm_sum"})

        assert actual == EXPECTED_RESULTS


def test_user_agent_strings():
    """
    The UA String parser should only care about selecting the right
    platform for Firefox UA strings.  Any non-firefox browser should
    get all available addons.
    """
    ua_strings = {
        "windows": "Mozilla/5.0 (Windows NT x.y; rv:10.0) Gecko/20100101 Firefox/10.0",
        "macintosh": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:60.0) Gecko/20100101 Firefox/60.0",
        "linux": "Mozilla/5.0 (X11; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0",
        "android": "Mozilla/5.0 (Android; Mobile; rv:40.0) Gecko/40.0 Firefox/40.0",
    }

    not_fx_ua_strings = [
        # Chrome
        "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",  # noqa
        # Microsoft Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",  # noqa
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",  # noqa
    ]

    # These are valid Firefox UA strings
    for platform, ua in ua_strings.items():
        platform_id = parse_ua(ua)
        assert OSNAME_TO_ID[platform] == platform_id

    # These are non-Firefox UA strings - we should expect nothing
    for ua in not_fx_ua_strings:
        actual_name = parse_ua(ua)
        assert actual_name is None
