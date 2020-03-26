# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.ensemble_recommender import (
    WeightCache,
    EnsembleRecommender,
)
from taar.recommenders.s3config import (
    TAAR_ENSEMBLE_BUCKET,
    TAAR_ENSEMBLE_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
)
from moto import mock_s3
import boto3
import json
import pytest
from .mocks import MockRecommenderFactory, MockRecommender

EXPECTED = {"collaborative": 1000, "similarity": 100, "locale": 10}

@pytest.fixture
def recommender_map_ctx(test_ctx):
    mock_locale = MockRecommender(
        {"def": 2.0, "efg": 2.1, "fgh": 2.2, "abc": 2.3}
    )
    mock_collaborative = MockRecommender(
        {"ghi": 3.0, "hij": 3.1, "ijk": 3.2, "def": 3.3}
    )
    mock_similarity = MockRecommender(
        {"jkl": 4.0, "klm": 4.1, "lmn": 4.2, "ghi": 4.3}
    )

    mock_recommender_map = {
        "collaborative": mock_collaborative,
        "similarity": mock_similarity,
        "locale": mock_locale,
    }

    test_ctx.set("mock_recommender_map", mock_recommender_map)
    return test_ctx

def install_mock_ensemble_data(ctx):
    DATA = {"ensemble_weights": EXPECTED}

    conn = boto3.resource(
        "s3",
        region_name="us-west-2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    conn.create_bucket(Bucket=TAAR_ENSEMBLE_BUCKET)
    conn.Object(TAAR_ENSEMBLE_BUCKET, TAAR_ENSEMBLE_KEY).put(
        Body=json.dumps(DATA)
    )

    return ctx



@mock_s3
def test_weight_cache(test_ctx):
    ctx = install_mock_ensemble_data(test_ctx)
    wc = WeightCache(ctx)
    actual = wc.getWeights()
    assert EXPECTED == actual


@mock_s3
def test_recommendations(recommender_map_ctx):
    ctx = install_mock_ensemble_data(recommender_map_ctx)

    EXPECTED_RESULTS = [
        ("ghi", 3430.0),
        ("def", 3320.0),
        ("ijk", 3200.0),
        ("hij", 3100.0),
        ("lmn", 420.0),
    ]

    r = EnsembleRecommender(ctx)
    client = {"client_id": "12345"}  # Anything will work here

    recommendation_list = r.recommend(client, 5)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS


@mock_s3
def test_preinstalled_guids(recommender_map_ctx):
    ctx = install_mock_ensemble_data(recommender_map_ctx)

    EXPECTED_RESULTS = [
        ("ghi", 3430.0),
        ("ijk", 3200.0),
        ("lmn", 420.0),
        ("klm", 409.99999999999994),
        ("abc", 23.0),
    ]
    
    r = EnsembleRecommender(ctx)

    # 'hij' should be excluded from the suggestions list
    # The other two addon GUIDs 'def' and 'jkl' will never be
    # recommended anyway and should have no impact on results
    client = {"client_id": "12345", "installed_addons": ["def", "hij", "jkl"]}

    recommendation_list = r.recommend(client, 5)
    print(recommendation_list)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
