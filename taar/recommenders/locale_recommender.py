import logging
from .base_recommender import AbstractRecommender

ADDON_LIST_BUCKET = 'telemetry-parquet'
ADDON_LIST_KEY = 'taar/locale/top10_dict.json'


logger = logging.getLogger(__name__)


class LocaleRecommender(AbstractRecommender):
    """ A recommender class that returns top N addons based on the client geo-locale.

    This will load a json file containing updated top n addons in use per geo locale
    updated periodically by a separate process on airflow using Longitdudinal Telemetry
    data.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """
    def __init__(self, ctx):
        self._ctx = ctx
        assert 'cache' in self._ctx
        self._init_from_ctx()

    def _init_from_ctx(self):
        cache = self._ctx['cache']
        self.top_addons_per_locale = cache.get_s3_json_content(ADDON_LIST_BUCKET,
                                                               ADDON_LIST_KEY)
        if self.top_addons_per_locale is None:
            logger.error("Cannot download the top per locale file {}".format(ADDON_LIST_KEY))

    def can_recommend(self, client_data, extra_data={}):
        # We can't recommend if we don't have our data files.
        if self.top_addons_per_locale is None:
            return False

        # If we have data coming from other sources, we can use that for
        # recommending.
        client_locale = client_data.get('locale', None) or extra_data.get('locale', None)
        if not isinstance(client_locale, str):
            return False

        if client_locale not in self.top_addons_per_locale:
            return False

        if not self.top_addons_per_locale.get(client_locale):
            return False

        return True

    def recommend(self, client_data, limit, extra_data={}):
        # If we have data coming from multiple sourecs, prefer the one
        # from 'client_data'.
        client_locale = client_data.get('locale') or extra_data.get('locale', None)
        result_list = self.top_addons_per_locale.get(client_locale, [])[:limit]
        return [(x, 1.0) for x in result_list]
