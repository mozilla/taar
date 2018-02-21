import boto3
import json
import pytest
from moto import mock_s3
from taar.recommenders.ensemble_recommender import S3_BUCKET
from taar.recommenders.ensemble_recommender import ENSEMBLE_WEIGHTS
from taar.recommenders.ensemble_recommender import EnsembleRecommender


class MockRecommender:
    """The MockRecommender takes in a map of GUID->weight."""

    def __init__(self, guid_map):
        self._guid_map = guid_map

    def can_recommend(self, *args, **kwargs):
        return True

    def recommend(self, *args, **kwargs):
        return sorted(self._guid_map.items(), key=lambda item: -item[1])


def generate_a_fake_taar_client():
    return {'client_id': 'test-client-001',
            'activeAddons': [],
            'geo_city': 'brasilia-br',
            'subsession_length': 4911,
            'locale': 'br-PT',
            'os': 'mac',
            'bookmark_count': 7,
            'tab_open_count': 4,
            'total_uri': 222,
            'unique_tlds': 21}


@pytest.fixture
def mock_s3_ensemble_weights():
    result_data = {'ensemble_weights': {'legacy': 10000,
                                        'collaborative': 1000,
                                        'similarity': 100,
                                        'locale': 10}}
    mock_s3().start()
    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=S3_BUCKET)
    conn.Object(S3_BUCKET, key=ENSEMBLE_WEIGHTS).put(Body=json.dumps(result_data))
    yield conn
    mock_s3().stop()


def test_recommendations(mock_s3_ensemble_weights):
    EXPECTED_RESULTS = [('cde', 12000.0),
                        ('bcd', 11000.0),
                        ('abc', 10023.0),
                        ('ghi', 3430.0),
                        ('def', 3320.0),
                        ('ijk', 3200.0),
                        ('hij', 3100.0),
                        ('lmn', 420.0),
                        ('klm', 409.99999999999994),
                        ('jkl', 400.0)]
    mock_legacy = MockRecommender({'abc': 1.0, 'bcd': 1.1, 'cde': 1.2})
    mock_locale = MockRecommender({'def': 2.0, 'efg': 2.1, 'fgh': 2.2, 'abc': 2.3})
    mock_collaborative = MockRecommender({'ghi': 3.0, 'hij': 3.1, 'ijk': 3.2, 'def': 3.3})
    mock_similarity = MockRecommender({'jkl': 4.0,  'klm': 4.1, 'lmn': 4.2, 'ghi': 4.3})
    mock_recommenders = {'legacy': mock_legacy,
                         'collaborative': mock_collaborative,
                         'similarity': mock_similarity,
                         'locale': mock_locale}
    r = EnsembleRecommender(mock_recommenders)
    client = generate_a_fake_taar_client()
    recommendation_list = r.recommend(client, 10)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
