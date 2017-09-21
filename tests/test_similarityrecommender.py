import boto3
import json
import numpy as np
import pytest
import scipy.stats
from moto import mock_s3
from taar.recommenders.similarity_recommender import \
    SimilarityRecommender, CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, S3_BUCKET


FAKE_DONOR_DATA = [
    {
        "activeAddons": ["{test-guid-1}", "{test-guid-2}", "{test-guid-3}", "{test-guid-4}"],
        "geo_city": "nowhere-us",
        "subsession_length": 1300,
        "locale": "en-US",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 32,
        "total_uri": 43,
        "unique_tlds": 500
    },
    {
        "activeAddons": ["{test-guid-5}", "{test-guid-6}", "{test-guid-7}", "{test-guid-8}"],
        "geo_city": "pompei-it",
        "subsession_length": 67832,
        "locale": "it-IT",
        "os": "Linux",
        "bookmark_count": 8166,
        "tab_open_count": 232,
        "total_uri": 42342,
        "unique_tlds": 1203
    },
    {
        "activeAddons": ["{test-guid-9}", "{test-guid-10}", "{test-guid-11}", "{test-guid-12}"],
        "geo_city": "brasilia-br",
        "subsession_length": 5411,
        "locale": "br-PT",
        "os": "windows",
        "bookmark_count": 17,
        "tab_open_count": 3,
        "total_uri": 432,
        "unique_tlds": 10
    }
]


def generate_fake_lr_curves(num_elements):
    lr_index = list(np.linspace(0, 10, num_elements))
    numerator_density = [scipy.stats.norm.pdf(float(i), 0.5, 0.5) for i in lr_index]
    denominator_density = [scipy.stats.norm.pdf(float(i), 5.0, 1.5) for i in lr_index]
    return list(zip(lr_index, zip(numerator_density, denominator_density)))


def generate_a_fake_taar_client():
    return {
        "client_id": "test-client-001",
        "activeAddons": [],
        "geo_city": "rio-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "windows",
        "bookmark_count": 57,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21
    }


@pytest.fixture
def instantiate_mocked_s3_bucket():
    mock_s3().start()

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=S3_BUCKET)
    # Write the fake addon donor data to the mocked S3.
    conn.Object(S3_BUCKET, key='taar/legacy/addon_donors.json').put(Body=json.dumps(FAKE_DONOR_DATA))
    # Write the fake lr curves data to the mocked S3.
    fake_lrs = generate_fake_lr_curves(1000)
    conn.Object(S3_BUCKET, key='taar/legacy/test/lr_curves.json').put(Body=json.dumps(fake_lrs))

    yield conn
    mock_s3().stop()


def test_can_recommend(instantiate_mocked_s3_bucket):
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

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


def test_recommendations(instantiate_mocked_s3_bucket):
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

    recommendations = r.recommend(generate_a_fake_taar_client(), 10)

    # Make sure the structure of the recommendations is correct and that we recommended the the right addons.
    assert isinstance(recommendations, list)

    # Make sure that the reported addons are the expected ones from the most similar donor.
    assert "{test-guid-9}" in recommendations
    assert "{test-guid-10}" in recommendations
    assert "{test-guid-11}" in recommendations
    assert "{test-guid-12}" in recommendations
    assert len(recommendations) == 4


def test_recommender_str(instantiate_mocked_s3_bucket):
    # Tests that the string representation of the recommender is correct.
    r = SimilarityRecommender()
    assert str(r) == "SimilarityRecommender"


def test_get_lr(instantiate_mocked_s3_bucket):
    # Tests that the likelihood ratio values are not empty for extreme values and are realistic.
    r = SimilarityRecommender()
    assert r.get_lr(0.0001) is not None
    assert r.get_lr(10.0) is not None
    assert r.get_lr(0.001) > r.get_lr(5.0)


def test_distance_functions(instantiate_mocked_s3_bucket):
    # Tests the similarity functions via expected output when passing modified client data.
    r = SimilarityRecommender()

    # Generate a fake client.
    test_client = generate_a_fake_taar_client()
    recs = r.recommend(test_client)
    assert len(recs) > 0

    # Make it a generally poor match for the donors.
    test_client.update({'total_uri': 10, 'bookmark_count': 2, 'subsession_length': 10})

    all_client_values_zero = test_client
    # Make all categorical variables non-matching with any donor.
    all_client_values_zero.update({key: 'zero' for key in test_client.keys() if key in CATEGORICAL_FEATURES})
    recs = r.recommend(all_client_values_zero)
    assert len(recs) == 0

    # Make all continuous variables equal to zero.
    all_client_values_zero.update({key: 0 for key in test_client.keys() if key in CONTINUOUS_FEATURES})
    recs = r.recommend(all_client_values_zero)
    assert len(recs) == 0

    # Make all categorical variables non-matching with any donor.
    all_client_values_high = test_client
    all_client_values_high.update({key: 'one billion' for key in test_client.keys() if key in CATEGORICAL_FEATURES})
    recs = r.recommend(all_client_values_high)
    assert len(recs) == 0

    # Make all continuous variables equal to a very high numerical value.
    all_client_values_high.update({key: 1e60 for key in test_client.keys() if key in CONTINUOUS_FEATURES})
    recs = r.recommend(all_client_values_high)
    assert len(recs) == 0

    # Test for 0.0 values if j_c is not normalized and j_d is fine.
    j_c = 0.0
    j_d = 0.42
    assert abs(j_c * j_d) == 0.0
    assert abs((j_c + 0.01) * j_d) != 0.0
