import boto3
import json
import numpy as np
import pytest
import scipy.stats
from moto import mock_s3
from taar.recommenders.similarity_recommender import \
    CATEGORICAL_FEATURES, CONTINUOUS_FEATURES, S3_BUCKET, DONOR_LIST_KEY, LR_CURVES_SIMILARITY_TO_PROBABILITY, \
    SimilarityRecommender
from .similarity_data import CONTINUOUS_FEATURE_FIXTURE_DATA
from .similarity_data import CATEGORICAL_FEATURE_FIXTURE_DATA


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
        "unique_tlds": 21
    }


@pytest.fixture
def mock_s3_categorical_data():
    mock_s3().start()

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=S3_BUCKET)
    # Write the fake addon donor data to the mocked S3.
    conn.Object(S3_BUCKET, key=DONOR_LIST_KEY).put(Body=json.dumps(CATEGORICAL_FEATURE_FIXTURE_DATA))
    # Write the fake lr curves data to the mocked S3.
    fake_lrs = generate_fake_lr_curves(1000)
    conn.Object(S3_BUCKET, key=LR_CURVES_SIMILARITY_TO_PROBABILITY).put(Body=json.dumps(fake_lrs))

    yield conn
    mock_s3().stop()


@pytest.fixture
def mock_s3_continuous_data():
    mock_s3().start()

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=S3_BUCKET)
    # Write the fake addon donor data to the mocked S3.
    conn.Object(S3_BUCKET, key=DONOR_LIST_KEY).put(Body=json.dumps(CONTINUOUS_FEATURE_FIXTURE_DATA))
    # Write the fake lr curves data to the mocked S3.
    fake_lrs = generate_fake_lr_curves(1000)
    conn.Object(S3_BUCKET, key=LR_CURVES_SIMILARITY_TO_PROBABILITY).put(Body=json.dumps(fake_lrs))

    yield conn
    mock_s3().stop()


@mock_s3
def test_soft_fail():
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

    # Don't recommend if the source files cannot be found.
    assert not r.can_recommend({})


def test_can_recommend(mock_s3_continuous_data):
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


def test_recommendations(mock_s3_continuous_data):
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

    # TODO: clobber the SimilarityRecommender::lr_curves

    recommendation_list = r.recommend(generate_a_fake_taar_client(), 1)

    assert isinstance(recommendation_list, list)
    assert len(recommendation_list) == 1

    recommendation, weight = recommendation_list[0]

    # Make sure that the reported addons are the expected ones from the most similar donor.
    assert "{test-guid-1}" == recommendation
    assert type(weight) == np.float64


def test_recommender_str(mock_s3_continuous_data):
    # Tests that the string representation of the recommender is correct.
    r = SimilarityRecommender()
    assert str(r) == "SimilarityRecommender"


def test_get_lr(mock_s3_continuous_data):
    # Tests that the likelihood ratio values are not empty for extreme values and are realistic.
    r = SimilarityRecommender()
    assert r.get_lr(0.0001) is not None
    assert r.get_lr(10.0) is not None
    assert r.get_lr(0.001) > r.get_lr(5.0)


def test_compute_clients_dist(mock_s3_continuous_data):
    # Test the distance function computation.
    r = SimilarityRecommender()
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
            "unique_tlds": 1
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
            "unique_tlds": 1
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
            "unique_tlds": 10
        }
    ]
    per_client_test = []

    # Compute a different set of distances for each set of clients.
    for tc in test_clients:
        test_distances = r.compute_clients_dist(tc)
        assert len(test_distances) == len(CONTINUOUS_FEATURE_FIXTURE_DATA)
        per_client_test.append(test_distances[2][0])

    # Ensure the different clients also had different distances to a specific donor.
    assert per_client_test[0] >= per_client_test[1] >= per_client_test[2]


def test_distance_functions(mock_s3_continuous_data):
    # Tests the similarity functions via expected output when passing modified client data.
    r = SimilarityRecommender()

    # Generate a fake client.
    test_client = generate_a_fake_taar_client()
    recs = r.recommend(test_client, 10)
    assert len(recs) > 0

    # Make it a generally poor match for the donors.
    test_client.update({'total_uri': 10, 'bookmark_count': 2, 'subsession_length': 10})

    all_client_values_zero = test_client
    # Make all categorical variables non-matching with any donor.
    all_client_values_zero.update({key: 'zero' for key in test_client.keys() if key in CATEGORICAL_FEATURES})
    recs = r.recommend(all_client_values_zero, 10)
    assert len(recs) == 0

    # Make all continuous variables equal to zero.
    all_client_values_zero.update({key: 0 for key in test_client.keys() if key in CONTINUOUS_FEATURES})
    recs = r.recommend(all_client_values_zero, 10)
    assert len(recs) == 0

    # Make all categorical variables non-matching with any donor.
    all_client_values_high = test_client
    all_client_values_high.update({key: 'one billion' for key in test_client.keys() if key in CATEGORICAL_FEATURES})
    recs = r.recommend(all_client_values_high, 10)
    assert len(recs) == 0

    # Make all continuous variables equal to a very high numerical value.
    all_client_values_high.update({key: 1e60 for key in test_client.keys() if key in CONTINUOUS_FEATURES})
    recs = r.recommend(all_client_values_high, 10)
    assert len(recs) == 0

    # Test for 0.0 values if j_c is not normalized and j_d is fine.
    j_c = 0.0
    j_d = 0.42
    assert abs(j_c * j_d) == 0.0
    assert abs((j_c + 0.01) * j_d) != 0.0


def test_weights_continuous(mock_s3_continuous_data):
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

    # In the ensemble method recommendations shoudl be a sorted list of tuples
    # containing [(guid, weight), (guid, weight)... (guid, weight)].
    recommendation_list = r.recommend(generate_a_fake_taar_client(), 2)
    with open('/tmp/similarity_recommender.json', 'w') as fout:
        fout.write(json.dumps(recommendation_list))

    # Make sure the structure of the recommendations is correct and
    # that we recommended the the right addons.

    assert len(recommendation_list) == 2
    for recommendation, weight in recommendation_list:
        assert isinstance(recommendation, str)
        assert isinstance(weight, float)

    # Test that sorting is appropriate.
    rec0 = recommendation_list[0]
    rec1 = recommendation_list[1]

    rec0_weight = rec0[1]
    rec1_weight = rec1[1]

    assert rec0_weight == rec1_weight > 0


def test_weights_categorical(mock_s3_categorical_data):
    '''
    This should get :
        ["{test-guid-1}", "{test-guid-2}", "{test-guid-3}", "{test-guid-4}"],
        ["{test-guid-9}", "{test-guid-10}", "{test-guid-11}", "{test-guid-12}"]
    from the first two entries in the sample data where the geo_city
    data

    '''
    # Create a new instance of a SimilarityRecommender.
    r = SimilarityRecommender()

    # In the ensemble method recommendations shoudl be a sorted list of tuples
    # containing [(guid, weight), (guid, weight)... (guid, weight)].
    recommendation_list = r.recommend(generate_a_fake_taar_client(), 2)

    assert len(recommendation_list) == 2
    # Make sure the structure of the recommendations is correct and that we recommended the the right addons.
    for recommendation, weight in recommendation_list:
        assert isinstance(recommendation, str)
        assert isinstance(weight, float)

    # Test that sorting is appropriate.
    rec0 = recommendation_list[0]
    rec1 = recommendation_list[1]

    rec0_weight = rec0[1]
    rec1_weight = rec1[1]

    assert rec0_weight == rec1_weight > 0
