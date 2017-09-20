import logging
from ..recommenders import utils
from .base_recommender import BaseRecommender

ADDON_LIST_BUCKET = 'telemetry-parquet'
ADDON_LIST_KEY = 'taar/legacy/legacy_dict.json'


logger = logging.getLogger(__name__)


class LegacyRecommender(BaseRecommender):
    """ A recommender class that returns potential replacements for deprecated legacy addons.

    This will load a json file (periodically updated) containing suggested web extension
    alternatives to legacy addons not compatible with Fx 57.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """
    def __init__(self):
        self.legacy_replacements = utils.get_s3_json_content(ADDON_LIST_BUCKET,
                                                             ADDON_LIST_KEY)
        if self.legacy_replacements is None:
            logger.error("Cannot download the JSON resource: {}".format(ADDON_LIST_KEY))

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self.legacy_replacements is None:
            return False

        # Get active addons from the client data and pull the legacy GUIDS.
        legacy_addons = client_data.get('disabled_addons_ids', None)

        # Can't use this recommender is no addons are installed.
        if not legacy_addons or not isinstance(legacy_addons, list):
            return False

        # If no member of the installed legacy addon guids can be found in the loaded resource
        # then no recommendation is possible.
        return len(set(legacy_addons).intersection(self.legacy_replacements.keys())) > 0

    def recommend(self, client_data, limit):
        legacy_addons = client_data.get('disabled_addons_ids', [])

        legacy_replacements = [self.legacy_replacements[client_addon_n]
                               for client_addon_n in legacy_addons if client_addon_n in self.legacy_replacements]

        recommendations = []
        # Flatten output recommendations.
        for addon_list in legacy_replacements:
            recommendations.extend(addon_list)

        # It is possible that some specific replacement addon recommendations are dropped if the number of viable
        # recommendations per installed legacy addons exceeds the recommendation list limit.
        num_recommendation = len(recommendations)
        if num_recommendation > limit:
            logger.warning("Recommendation list truncated",
                           extra={"limit": limit, "num_recommendations": num_recommendation})

        return recommendations[:limit]
