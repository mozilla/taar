import logging
from .base_recommender import AbstractRecommender

ADDON_LIST_BUCKET = 'telemetry-parquet'
ADDON_LIST_KEY = 'taar/legacy/legacy_dict.json'


logger = logging.getLogger(__name__)


class LegacyRecommender(AbstractRecommender):
    """ A recommender class that returns potential replacements for deprecated legacy addons.

    This will load a json file (periodically updated) containing suggested web extension
    alternatives to legacy addons not compatible with Fx 57.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """
    def __init__(self, ctx):
        self._ctx = ctx
        assert 'cache' in self._ctx
        self._init_from_ctx()

    def _init_from_ctx(self):
        self.legacy_replacements = self._ctx['cache'].get_s3_json_content(ADDON_LIST_BUCKET,
                                                                          ADDON_LIST_KEY)
        if self.legacy_replacements is None:
            logger.error("Cannot download the JSON resource: {}".format(ADDON_LIST_KEY))

    def can_recommend(self, client_data, extra_data={}):
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

    def recommend(self, client_data, limit, extra_data={}):
        legacy_addons = client_data.get('disabled_addons_ids', [])

        replacements = [self.legacy_replacements[legacy_addon]
                        for legacy_addon in legacy_addons
                        if legacy_addon in self.legacy_replacements]

        recommendations = []
        while len(recommendations) < limit and len(replacements) > 0:
            remove_list = []
            for idx, replace_list in enumerate(replacements):
                if len(replace_list) == 0:
                    remove_list.append(idx)
                    continue
                recommendations.append((replace_list.pop(0), 1))
            remove_list.reverse()
            for idx in remove_list:
                del replacements[idx]

        return recommendations
