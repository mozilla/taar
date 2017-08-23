import logging
from ..recommenders import utils


ADDON_LIST_BUCKET = 'telemetry-private-analysis-2'
ADDON_LIST_KEY = 'mdoglio_top10_addons/top10_dict.json'


logger = logging.getLogger(__name__)


class LocaleRecommender:
    """ A recommender class that returns top N addons based on the client geo-locale.

    This will load a json file containing updated top n addons in use per geo locale
    updated periodically by a separate process on airflow using Longitdudinal Telemetry
    data.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """
    def __init__(self):
        self.top_addons_per_locale = utils.get_s3_json_content(ADDON_LIST_BUCKET,
                                                               ADDON_LIST_KEY)
        if self.top_addons_per_locale is None:
            logger.error("Cannot download the top per locale file {}".format(ADDON_LIST_KEY))

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self.top_addons_per_locale is None:
            return False
        client_locale = client_data.get('locale', None)
        if not isinstance(client_locale, str):
            return False

        if client_locale not in self.top_addons_per_locale:
            return False

        if not self.top_addons_per_locale.get(client_locale):
            return False

        return True

    def recommend(self, client_data, limit):
        client_locale = client_data.get('locale')
        return self.top_addons_per_locale.get(client_locale, [])[:limit]
