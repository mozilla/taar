import logging
from taar.recommenders.ensemble_recommender import EnsembleRecommender


logger = logging.getLogger(__name__)


class RecommenderFactory:
    """
    A RecommenderFactory provides support to create recommenders.

    The existence of a factory enables injection of dependencies into
    the RecommendationManager and eases the implementation of test
    harnesses.
    """
    def __init__(self, ctx):
        self._ctx = ctx
        self._recommender_factory_map = self._ctx['recommender_factory_map']

    def get_names(self):
        return self._recommender_factory_map.keys()

    def create(self, recommender_name):
        return self._recommender_factory_map[recommender_name]()


class RecommendationManager:
    """This class determines which of the set of recommendation
    engines will actually be used to generate recommendations."""

    LINEAR_RECOMMENDER_ORDER = ['legacy', 'collaborative', 'similarity', 'locale']

    def __init__(self, ctx):
        """Initialize the user profile fetcher and the recommenders.
        """
        self._ctx = ctx

        assert 'recommender_factory' in self._ctx
        assert 'profile_fetcher' in self._ctx

        recommender_factory = ctx['recommender_factory']
        profile_fetcher = ctx['profile_fetcher']

        self.profile_fetcher = profile_fetcher
        self.linear_recommenders = []
        self._recommender_map = {}

        logger.info("Initializing recommenders")
        for rkey in self.LINEAR_RECOMMENDER_ORDER:
            recommender = recommender_factory.create(rkey)

            self.linear_recommenders.append(recommender)
            self._recommender_map[rkey] = recommender

        # Install the recommender_map to the context and instantiate
        # the EnsembleRecommender
        self._ctx['recommender_map'] = self._recommender_map
        self._recommender_map['ensemble'] = EnsembleRecommender(self._ctx.child())

    def recommend(self, client_id, limit, extra_data={}):
        """Return recommendations for the given client.

        The recommendation logic will go through each recommender and
        pick the first one that "can_recommend".

        :param client_id: the client unique id.
        :param limit: the maximum number of recommendations to return.
        :param extra_data: a dictionary with extra client data.
        """
        # Get the info for the requested client id.
        client_info = self.profile_fetcher.get(client_id)
        if client_info is None:
            return []

        # Compute the recommendation.

        # Select recommendation output based on extra_data['branch']
        branch_selector = extra_data.get('branch', 'control')
        if branch_selector not in ('control', 'linear', 'ensemble'):
            return []
        branch_method = getattr(self, 'recommend_%s' % branch_selector)
        return branch_method(client_info, client_id, limit, extra_data)

    def recommend_control(self, client_info, client_id, limit, extra_data):
        """Run the control recommender - that is nothing"""
        return []

    def recommend_ensemble(self, client_info, client_id, limit, extra_data):
        """Run the ensemble recommender """
        recommender = self._recommender_map['ensemble']
        return recommender.recommend(client_info, limit, extra_data)

    def recommend_linear(self, client_info, client_id, limit, extra_data):
        """Run the linear recommender"""
        for r in self.linear_recommenders:
            if r.can_recommend(client_info, extra_data):
                logger.info("Recommender selected", extra={
                    "client_id": client_id, "recommender": str(r)
                })
                recommendations = r.recommend(client_info, limit, extra_data)
                if not recommendations:
                    logger.info("No recommendations", extra={
                        "client_id": client_id, "recommender": str(r)
                    })
                else:
                    logger.info("Recommendations served", extra={
                        "client_id": client_id, "recommended_addons": str(recommendations)
                    })
                return recommendations
        logger.info("No recommender can recommend addons", extra={
            "client_id": client_id
        })
        return []
