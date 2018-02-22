# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import json
import pytest
from moto import mock_s3
from taar.recommenders.ensemble_recommender import S3_BUCKET
from taar.recommenders.ensemble_recommender import ENSEMBLE_WEIGHTS
from taar.recommenders import EnsembleRecommender
from taar.recommenders import RecommendationManager
from .mocks import MockRecommenderFactory


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

    factory = MockRecommenderFactory()
    mock_recommender_map = {'legacy': factory.create('legacy'),
                            'collaborative': factory.create('collaborative'),
                            'similarity': factory.create('similarity'),
                            'locale': factory.create('locale')}
    r = EnsembleRecommender(mock_recommender_map)
    client = {}  # Anything will work here
    recommendation_list = r.recommend(client, 10)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS


def test_recommendations_via_manager(mock_s3_ensemble_weights):
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

    factory = MockRecommenderFactory()

    class MockProfileFetcher:
        def get(self, client_id):
            return {}

    manager = RecommendationManager(factory, MockProfileFetcher())
    recommendation_list = manager.recommend('some_ignored_id', 10, extra_data={'branch': 'ensemble'})
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
