from taar.context import Context
from taar.recommenders.ensemble_recommender import WeightCache, EnsembleRecommender
from .mocks import MockRecommenderFactory

EXPECTED = {'collaborative': 1000,
            'similarity': 100,
            'locale': 10}


class Mocker:
    def get_s3_json_content(self, *args, **kwargs):
        return {'ensemble_weights': EXPECTED}


def test_weight_cache():   # noqa

    ctx = Context()
    ctx['utils'] = Mocker()

    wc = WeightCache(ctx.child())
    actual = wc.getWeights()
    assert EXPECTED == actual


def test_recommendations():
    ctx = Context()

    ctx['utils'] = Mocker()

    EXPECTED_RESULTS = [('ghi', 3430.0),
                        ('def', 3320.0),
                        ('ijk', 3200.0),
                        ('hij', 3100.0),
                        ('lmn', 420.0),
                        ('klm', 409.99999999999994),
                        ('jkl', 400.0),
                        ('abc', 23.0),
                        ('fgh', 22.0),
                        ('efg', 21.0)]

    factory = MockRecommenderFactory()
    ctx['recommender_factory'] = factory

    ctx['recommender_map'] = {'collaborative': factory.create('collaborative'),
                              'similarity': factory.create('similarity'),
                              'locale': factory.create('locale')}
    r = EnsembleRecommender(ctx.child())
    client = {'client_id': '12345'}  # Anything will work here
    recommendation_list = r.recommend(client, 10)
    assert isinstance(recommendation_list, list)
    assert recommendation_list == EXPECTED_RESULTS
