from .utils import fetch_json

# TODO: this should be a public s3 bucket IFF we are allowed
# to share this info publically.
ADDON_LIST_PER_LOCALE_URL = \
    'http://www.thiswillonedaybearealurl.com/amazing_things.json'


class LocaleRecommender:
    """ A recommender class that returns top N addons based on the client geo-locale.

    This will load a json file containing updated top n addons in use per geo locale
    updated periodically by a separate process on airflow using Longitdudinal Telemetry
    data.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """
    def __init__(self):
        self.top_addons_per_locale = fetch_json(ADDON_LIST_PER_LOCALE_URL)

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
