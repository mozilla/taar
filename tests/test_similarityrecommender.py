# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import six
import logging

import pickle
import numpy as np
import scipy.stats
from srgutil.cache import LazyJSONLoader

import boto3
from moto import mock_s3

from taar.recommenders.similarity_recommender import (
    CATEGORICAL_FEATURES,
    CONTINUOUS_FEATURES,
    SimilarityRecommender,
)

from .similarity_data import CONTINUOUS_FEATURE_FIXTURE_DATA
from .similarity_data import CATEGORICAL_FEATURE_FIXTURE_DATA

from taar.recommenders.s3config import (
    TAAR_SIMILARITY_BUCKET,
    TAAR_SIMILARITY_DONOR_KEY,
    TAAR_SIMILARITY_LRCURVES_KEY,
)


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


def install_no_data(ctx):
    conn = boto3.resource("s3", region_name="us-west-2")

    conn.create_bucket(Bucket=TAAR_SIMILARITY_BUCKET)
    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY).put(Body="")

    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY).put(Body="")

    ctx.set("similarity_donors_pool", LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY
    ))

    ctx.set("similarity_lr_curves", LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY
    ))

    return ctx


def install_categorical_data(ctx):
    conn = boto3.resource("s3", region_name="us-west-2")

    try:
        conn.create_bucket(Bucket=TAAR_SIMILARITY_BUCKET)
    except Exception:
        pass
    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY).put(
        Body=json.dumps(CATEGORICAL_FEATURE_FIXTURE_DATA)
    )

    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY).put(
        Body=json.dumps(generate_fake_lr_curves(1000))
    )

    ctx.set("similarity_donors_pool",  LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY
    ))

    ctx.set("similarity_lr_curves", LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY
    ))

    return ctx


def install_continuous_data(ctx):
    cts_data = json.dumps(CONTINUOUS_FEATURE_FIXTURE_DATA)
    lrs_data = json.dumps(generate_fake_lr_curves(1000))

    conn = boto3.resource("s3", region_name="us-west-2")

    try:
        conn.create_bucket(Bucket=TAAR_SIMILARITY_BUCKET)
    except Exception:
        pass
    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY).put(Body=cts_data)

    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY).put(Body=lrs_data)

    ctx.set("similarity_donors_pool", LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY
    ))

    ctx.set("similarity_lr_curves", LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY
    ))

    return ctx


def check_matrix_built(caplog):
    msg = "Reconstructed matrices for similarity recommender"
    return sum([msg in str(s) for s in caplog.records]) > 0

@mock_s3
def test_can_pickle(test_ctx):

    test_ctx = install_continuous_data(test_ctx)

    r = SimilarityRecommender(test_ctx)
    restored = pickle.loads(pickle.dumps(r))
    assert restored._ctx.get("similarity_donors_pool", None) is not None
    assert restored._ctx.get("similarity_lr_curves", None) is not None



@mock_s3
def test_soft_fail(test_ctx, caplog):
    # Create a new instance of a SimilarityRecommender.
    ctx = install_no_data(test_ctx)
    r = SimilarityRecommender(ctx)

    # Don't recommend if the source files cannot be found.
    assert not r.can_recommend({})
    assert not check_matrix_built(caplog)


@mock_s3
def test_can_recommend(test_ctx, caplog):
    caplog.set_level(logging.INFO)

    # Create a new instance of a SimilarityRecommender.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)

    assert check_matrix_built(caplog)

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


@mock_s3
def test_recommendations(test_ctx):
    # Create a new instance of a SimilarityRecommender.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)

    recommendation_list = r.recommend(generate_a_fake_taar_client(), 1)

    assert isinstance(recommendation_list, list)
    assert len(recommendation_list) == 1

    recommendation, weight = recommendation_list[0]

    # Make sure that the reported addons are the expected ones from the most similar donor.
    assert "{test-guid-1}" == recommendation
    assert type(weight) == np.float64


@mock_s3
def test_recommender_str(test_ctx):
    # Tests that the string representation of the recommender is correct.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)
    assert str(r) == "SimilarityRecommender"


@mock_s3
def test_get_lr(test_ctx):
    # Tests that the likelihood ratio values are not empty for extreme values and are realistic.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)
    assert r.get_lr(0.0001) is not None
    assert r.get_lr(10.0) is not None
    assert r.get_lr(0.001) > r.get_lr(5.0)


@mock_s3
def test_compute_clients_dist(test_ctx):
    # Test the distance function computation.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)
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
    for tc in test_clients:
        test_distances = r.compute_clients_dist(tc)
        assert len(test_distances) == len(CONTINUOUS_FEATURE_FIXTURE_DATA)
        per_client_test.append(test_distances[2][0])

    # Ensure the different clients also had different distances to a specific donor.
    assert per_client_test[0] >= per_client_test[1] >= per_client_test[2]


@mock_s3
def test_distance_functions(test_ctx):
    # Tests the similarity functions via expected output when passing modified client data.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)

    # Generate a fake client.
    test_client = generate_a_fake_taar_client()
    recs = r.recommend(test_client, 10)
    assert len(recs) > 0

    # Make it a generally poor match for the donors.
    test_client.update({"total_uri": 10, "bookmark_count": 2, "subsession_length": 10})

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


@mock_s3
def test_weights_continuous(test_ctx):
    # Create a new instance of a SimilarityRecommender.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)

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


@mock_s3
def test_weights_categorical(test_ctx):
    """
    This should get :
        ["{test-guid-1}", "{test-guid-2}", "{test-guid-3}", "{test-guid-4}"],
        ["{test-guid-9}", "{test-guid-10}", "{test-guid-11}", "{test-guid-12}"]
    from the first two entries in the sample data where the geo_city
    data

    """
    # Create a new instance of a SimilarityRecommender.
    test_ctx = install_categorical_data(test_ctx)
    test_ctx = install_continuous_data(test_ctx)

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


@mock_s3
def test_recompute_matrices(test_ctx, caplog):
    caplog.set_level(logging.INFO)

    # Create a new instance of a SimilarityRecommender.
    ctx = install_continuous_data(test_ctx)
    r = SimilarityRecommender(ctx)

    # Reloading the donors pool should reconstruct the matrices
    caplog.clear()
    r._donors_pool.force_expiry()
    r.donors_pool
    assert check_matrix_built(caplog)

    # Reloading the LR curves should reconstruct the matrices
    caplog.clear()
    r._lr_curves.force_expiry()
    r.lr_curves
    assert check_matrix_built(caplog)
