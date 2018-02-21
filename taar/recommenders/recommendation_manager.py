import logging
from .collaborative_recommender import CollaborativeRecommender
from .legacy_recommender import LegacyRecommender
from .locale_recommender import LocaleRecommender
from .similarity_recommender import SimilarityRecommender
from .ensemble_recommender import EnsembleRecommender
from ..profile_fetcher import ProfileFetcher


logger = logging.getLogger(__name__)


class RecommendationManager(object):
    """This class determines which of the set of recommendation
    engines will actually be used to generate recommendations."""

    def __init__(self, profile_fetcher=None):
        """Initialize the user profile fetcher and the recommenders.
        """
        if profile_fetcher is None:
            logger.info("Initializing profile_fetcher")
            self.profile_fetcher = ProfileFetcher()
        else:
            self.profile_fetcher = profile_fetcher

        self._recommender_map = {'legacy': LegacyRecommender(),
                                 'collaborative': CollaborativeRecommender(),
                                 'similarity': SimilarityRecommender(),
                                 'locale': LocaleRecommender()}

        self._recommender_map['ensemble'] = EnsembleRecommender(self._recommenders)

        logger.info("Initializing recommenders")
        self.linear_recommenders = (self._recommender_map['legacy'],
                                    self._recommender_map['collaborative'],
                                    self._recommender_map['similarity'],
                                    self._recommender_map['locale'])

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
