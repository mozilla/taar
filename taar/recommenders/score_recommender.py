import numpy as np
import operator as op
import requests

PROTO_USERS_MODEL_URL =\
    "url to a white list of interpolated addon donors"

SS_VS_DS_SCORES_MODEL_URL =\
    "url to the parameters of a same source versus different source model (two distributions)"

def fetch_json(uri):
    """ Perform an HTTP GET on the given uri, return the results as json.
    If there is an error fetching the data, raise an exception.

    Args:
        uri: the string URI to fetch.

    Returns:
        A JSON object with the response.
    """
    data = requests.get(uri)
    # Raise an exception if the fetch failed.
    data.raise_for_status()
    return data.json()


class ScoreRecommender:
    """ The addon recommendation interface to the score-based model.

    Usage example::

        recommender = CollaborativeRecommender()
        dists = recommender.recommend(client_info)
    """
    #TODO: replace the above description with real documentation

    def __init__(self):
        # Download the addon mappings.
        self.addon_mapping = fetch_json(ADDON_MAPPING_URL)
        self.model = None
        self.raw_item_matrix = None

        self._load_model()

    def _load_model(self):
        # Download the JSON item matrix.
        self.raw_item_matrix = fetch_json(ADDON_MODEL_URL)

        # Build a dense numpy matrix out of it.
        num_rows = len(self.raw_item_matrix)
        num_cols = len(self.raw_item_matrix[0]['features'])

        self.model = np.zeros(shape=(num_rows, num_cols))
        for index, row in enumerate(self.raw_item_matrix):
            self.model[index, :] = row['features']

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self.raw_item_matrix is None or self.model is None or self.addon_mapping is None:
            return False

        # We only get meaningful recommendation if a client has at least an
        # addon installed.
        # TODO: should we exclude system addons?
        if len(client_data.get('installed_addons', [])) > 0:
            return True

        return False

    def recommend(self, client_data, limit):
        # Addons identifiers are stored as positive hash values within the model.
        features_of_interest = client_data.get('features_of_interest_inner', [])

        # Build the query vector by setting the position of the queried addons to 1.0
        # and the other to 0.0.
        comparion_vector = np.array([1.0 if (entry.get("id") in installed_addons) else 0.0
                                 for entry in self.raw_item_matrix])

        # Build the user factors matrix.
        user_factors = np.matmul(query_vector, self.model)
        user_factors_transposed = np.transpose(user_factors)

        # Compute the distance between the user and all the addons in the latent
        # space.
        distances = {}
        for addon in self.raw_item_matrix:
            # We don't really need to show the items we requested. They will always
            # end up with the greatest score.
            if addon.get("id") in installed_addons:
                continue

            dist = np.dot(user_factors_transposed, addon.get('features'))
            # TODO: The next function should read the addon ids from the "addon_mapping"
            # looking them up by 'id' (which is an hashed value).
            addon_id = str(addon.get('id'))  # self.addon_mapping[str(addon.get('id'))]
            distances[addon_id] = dist

        # Sort the suggested addons by their score and return the sorted list of addon
        # ids.
        sorted_dists = sorted(distances.items(), key=op.itemgetter(1), reverse=True)
        return [s[0] for s in sorted_dists[:limit]]
