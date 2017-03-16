class EmptyRecommender:
    """ A bogus recommender class that always returns an empty list.

    This will always be able to recommend an empty list and should be added
    as the lowest priority recommender in the recommendation chain.
    """

    def can_recommend(self, client_data):
        return True

    def recommend(self, client_data, limit):
        return []
