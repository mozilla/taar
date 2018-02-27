from taar.recommenders import EnsembleRecommender, WeightCache
from .mocks import MockRecommenderFactory    # noqa
from .mocks import mock_s3_ensemble_weights  # noqa
import pytest

def test_weight_cache(mock_s3_ensemble_weights):   # noqa
    wc = WeightCache()
    actual = wc.getWeights()
    expected = {'legacy': 10000,
                'collaborative': 1000,
                'similarity': 100,
                'locale': 10}
    assert expected == actual


@pytest.mark.skip(reason="moto breaks this test")  # noqa
def test_recommendations(mock_s3_ensemble_weights):   # noqa
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
