from taar.recommenders.empty_recommender import EmptyRecommender


def test_can_recommend():
    # Tests that the empty recommender can always recommend.
    r = EmptyRecommender()
    assert r.can_recommend({})


def test_empty_recommendations():
    # Tests that the empty recommender always recommends an empty list
    # of addons.
    r = EmptyRecommender()
    recommendations = r.recommend({}, 1)
    assert isinstance(recommendations, list)
    assert len(recommendations) == 0
