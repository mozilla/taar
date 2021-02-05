# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import six
import logging

import numpy as np
import scipy.stats

from taar.interfaces import ITAARCache
from taar.recommenders.similarity_recommender import (
    CATEGORICAL_FEATURES,
    CONTINUOUS_FEATURES,
    SimilarityRecommender,
)

from .similarity_data import CONTINUOUS_FEATURE_FIXTURE_DATA
from .similarity_data import CATEGORICAL_FEATURE_FIXTURE_DATA

import fakeredis
import mock
import contextlib
from .noop_fixtures import (
    noop_taarcollab_dataload,
    noop_taarlite_dataload,
    noop_taarlocale_dataload,
    noop_taarensemble_dataload,
)
from taar.recommenders.redis_cache import TAARCacheRedis


def noop_loaders(stack):
    stack = noop_taarlocale_dataload(stack)
    stack = noop_taarcollab_dataload(stack)
    stack = noop_taarensemble_dataload(stack)
    stack = noop_taarlite_dataload(stack)
    return stack


def generate_fake_lr_curves(num_elements, ceiling=10.0):
    """
    Generate a mock likelihood ratio (LR) curve that can be used for
    testing.
    """
    lr_index = list(np.linspace(0, ceiling, num_elements))

    # This sets up a normal distribution with a mean of 0.5 and std
    # deviation of 0.5
    numerator_density = [scipy.stats.norm.pdf(float(i), 0.5, 0.5) for i in lr_index]

    # This sets up a normal distribution with a mean of 5.0 and std
    # deviation of 1.5.  So this is right shifted and has a wide std
    # deviation compared to the first curve.

    # This results in a small overlap.  Using ranges between 0.5 to
    # 5.0 will yield large values to small values.
    denominator_density = [scipy.stats.norm.pdf(float(i), 5.0, 1.5) for i in lr_index]
    return list(zip(lr_index, zip(numerator_density, denominator_density)))


def generate_a_fake_taar_client():
    return {
        "client_id": "test-client-001",
        "activeAddons": [],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    }


@contextlib.contextmanager
def mock_install_no_data(ctx):
    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None
        stack.enter_context(
            mock.patch.object(TAARCacheRedis, "_fetch_similarity_donors", return_value="", )
        )

        stack.enter_context(
            mock.patch.object(TAARCacheRedis, "_fetch_similarity_lrcurves", return_value="", )
        )

        stack = noop_loaders(stack)

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


@contextlib.contextmanager
def mock_install_categorical_data(ctx):
    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "_fetch_similarity_donors",
                return_value=CATEGORICAL_FEATURE_FIXTURE_DATA,
            )
        )

        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis,
                "_fetch_similarity_lrcurves",
                return_value=generate_fake_lr_curves(1000),
            )
        )
        stack = noop_loaders(stack)

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


@contextlib.contextmanager
def mock_install_continuous_data(ctx):
    cts_data = CONTINUOUS_FEATURE_FIXTURE_DATA
    lrs_data = generate_fake_lr_curves(1000)

    with contextlib.ExitStack() as stack:
        TAARCacheRedis._instance = None
        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_similarity_donors", return_value=cts_data,
            )
        )

        stack.enter_context(
            mock.patch.object(
                TAARCacheRedis, "_fetch_similarity_lrcurves", return_value=lrs_data,
            )
        )
        stack = noop_loaders(stack)

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


def test_soft_fail(test_ctx, caplog):
    # Create a new instance of a SimilarityRecommender.
    with mock_install_no_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        # Don't recommend if the source files cannot be found.
        assert not r.can_recommend({})


def test_can_recommend(test_ctx, caplog):
    caplog.set_level(logging.INFO)

    # Create a new instance of a SimilarityRecommender.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        # Test that we can't recommend if we have not enough client info.
        assert not r.can_recommend({})

        # Test that we can recommend for a normal client.
        assert r.can_recommend(generate_a_fake_taar_client())

        # Check that we can not recommend if any required client field is missing.
        required_fields = CATEGORICAL_FEATURES + CONTINUOUS_FEATURES

        for required_field in required_fields:
            profile_without_x = generate_a_fake_taar_client()

            # Make an empty value in a required field in the client info dict.
            profile_without_x[required_field] = None
            assert not r.can_recommend(profile_without_x)

            # Completely remove (in place) the entire required field from the dict.
            del profile_without_x[required_field]
            assert not r.can_recommend(profile_without_x)


def test_recommendations(test_ctx):
    # Create a new instance of a SimilarityRecommender.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        recommendation_list = r.recommend(generate_a_fake_taar_client(), 1)

        assert isinstance(recommendation_list, list)
        assert len(recommendation_list) == 1

        recommendation, weight = recommendation_list[0]

        # Make sure that the reported addons are the expected ones from the most similar donor.
        assert "{test-guid-1}" == recommendation
        assert type(weight) == np.float64


def test_get_lr(test_ctx):
    # Tests that the likelihood ratio values are not empty for extreme values and are realistic.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)
        cache = r._get_cache({})
        assert r.get_lr(0.0001, cache) is not None
        assert r.get_lr(10.0, cache) is not None
        assert r.get_lr(0.001, cache) > r.get_lr(5.0, cache)


def test_compute_clients_dist(test_ctx):
    # Test the distance function computation.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)
        test_clients = [
            {
                "client_id": "test-client-002",
                "activeAddons": [],
                "geo_city": "sfo-us",
                "subsession_length": 1,
                "locale": "en-US",
                "os": "windows",
                "bookmark_count": 1,
                "tab_open_count": 1,
                "total_uri": 1,
                "unique_tlds": 1,
            },
            {
                "client_id": "test-client-003",
                "activeAddons": [],
                "geo_city": "brasilia-br",
                "subsession_length": 1,
                "locale": "br-PT",
                "os": "windows",
                "bookmark_count": 10,
                "tab_open_count": 1,
                "total_uri": 1,
                "unique_tlds": 1,
            },
            {
                "client_id": "test-client-004",
                "activeAddons": [],
                "geo_city": "brasilia-br",
                "subsession_length": 100,
                "locale": "br-PT",
                "os": "windows",
                "bookmark_count": 10,
                "tab_open_count": 10,
                "total_uri": 100,
                "unique_tlds": 10,
            },
        ]
        per_client_test = []

        # Compute a different set of distances for each set of clients.
        cache = r._get_cache({})
        for tc in test_clients:
            test_distances = r.compute_clients_dist(tc, cache)
            assert len(test_distances) == len(CONTINUOUS_FEATURE_FIXTURE_DATA)
            per_client_test.append(test_distances[2][0])

        # Ensure the different clients also had different distances to a specific donor.
        assert per_client_test[0] >= per_client_test[1] >= per_client_test[2]


def test_distance_functions(test_ctx):
    # Tests the similarity functions via expected output when passing
    # modified client data.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        # Generate a fake client.
        test_client = generate_a_fake_taar_client()
        recs = r.recommend(test_client, 10)
        assert len(recs) > 0

        # Make it a generally poor match for the donors.
        test_client.update(
            {"total_uri": 10, "bookmark_count": 2, "subsession_length": 10}
        )

        all_client_values_zero = test_client
        # Make all categorical variables non-matching with any donor.
        all_client_values_zero.update(
            {key: "zero" for key in test_client.keys() if key in CATEGORICAL_FEATURES}
        )
        recs = r.recommend(all_client_values_zero, 10)
        assert len(recs) == 0

        # Make all continuous variables equal to zero.
        all_client_values_zero.update(
            {key: 0 for key in test_client.keys() if key in CONTINUOUS_FEATURES}
        )
        recs = r.recommend(all_client_values_zero, 10)
        assert len(recs) == 0

        # Make all categorical variables non-matching with any donor.
        all_client_values_high = test_client
        all_client_values_high.update(
            {
                key: "one billion"
                for key in test_client.keys()
                if key in CATEGORICAL_FEATURES
            }
        )
        recs = r.recommend(all_client_values_high, 10)
        assert len(recs) == 0

        # Make all continuous variables equal to a very high numerical value.
        all_client_values_high.update(
            {key: 1e60 for key in test_client.keys() if key in CONTINUOUS_FEATURES}
        )
        recs = r.recommend(all_client_values_high, 10)
        assert len(recs) == 0

        # Test for 0.0 values if j_c is not normalized and j_d is fine.
        j_c = 0.0
        j_d = 0.42
        assert abs(j_c * j_d) == 0.0
        assert abs((j_c + 0.01) * j_d) != 0.0


def test_weights_continuous(test_ctx):
    # Create a new instance of a SimilarityRecommender.
    with mock_install_continuous_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        # In the ensemble method recommendations should be a sorted list of tuples
        # containing [(guid, weight), (guid, weight)... (guid, weight)].
        recommendation_list = r.recommend(generate_a_fake_taar_client(), 2)
        with open("/tmp/similarity_recommender.json", "w") as fout:
            fout.write(json.dumps(recommendation_list))

        # Make sure the structure of the recommendations is correct and
        # that we recommended the the right addons.

        assert len(recommendation_list) == 2
        for recommendation, weight in recommendation_list:
            assert isinstance(recommendation, six.string_types)
            assert isinstance(weight, float)

        # Test that sorting is appropriate.
        rec0 = recommendation_list[0]
        rec1 = recommendation_list[1]

        rec0_weight = rec0[1]
        rec1_weight = rec1[1]

        # Duplicate presence of test-guid-1 should mean rec0_weight is double
        # rec1_weight, and both should be greater than 1.0

        assert rec0_weight > rec1_weight > 1.0


def test_weights_categorical(test_ctx):
    """
    This should get :
        ["{test-guid-1}", "{test-guid-2}", "{test-guid-3}", "{test-guid-4}"],
        ["{test-guid-9}", "{test-guid-10}", "{test-guid-11}", "{test-guid-12}"]
    from the first two entries in the sample data where the geo_city
    data

    """
    # Create a new instance of a SimilarityRecommender.
    with mock_install_categorical_data(test_ctx):
        r = SimilarityRecommender(test_ctx)

        # In the ensemble method recommendations should be a sorted list of tuples
        # containing [(guid, weight), (guid, weight)... (guid, weight)].
        recommendation_list = r.recommend(generate_a_fake_taar_client(), 2)

        assert len(recommendation_list) == 2
        # Make sure the structure of the recommendations is correct and that we recommended the the right addons.
        for recommendation, weight in recommendation_list:
            assert isinstance(recommendation, six.string_types)
            assert isinstance(weight, float)

        # Test that sorting is appropriate.
        rec0 = recommendation_list[0]
        rec1 = recommendation_list[1]

        rec0_weight = rec0[1]
        rec1_weight = rec1[1]

        assert rec0_weight > rec1_weight > 0
