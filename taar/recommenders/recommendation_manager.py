import logging
from .collaborative_recommender import CollaborativeRecommender
from .locale_recommender import LocaleRecommender
from .empty_recommender import EmptyRecommender
from ..profile_fetcher import ProfileFetcher


logger = logging.getLogger(__name__)


class RecommendationManager:

    def __init__(self, profile_fetcher=None, recommenders=None):
        # Instantiate the object to get the client info.
        if profile_fetcher is None:
            logger.info("Initializing profile_fetcher")
            self.profile_fetcher = ProfileFetcher()
        else:
            self.profile_fetcher = profile_fetcher

        # Init the recommenders. Note: ORDER MATTERS!
        # The recommendation logic will go through each recommender and pick the
        # first one that "can_recommend".
        if not recommenders:
            logger.info("Initializing recommenders")
            self.recommenders = (
                CollaborativeRecommender(),
                LocaleRecommender(),
                EmptyRecommender()
            )
        else:
            self.recommenders = recommenders

    def recommend(self, client_id, limit):
        # Get the info for the requested client id.
        client_info = self.profile_fetcher.get(client_id)

        # Compute the recommendation.
        for r in self.recommenders:
            if r.can_recommend(client_info):
                return r.recommend(client_info, limit)
