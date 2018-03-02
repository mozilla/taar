import logging
import numpy as np
import operator as op

from .base_recommender import AbstractRecommender

ADDON_MODEL_URL =\
    "https://s3-us-west-2.amazonaws.com/telemetry-public-analysis-2/telemetry-ml/addon_recommender/item_matrix.json"
ADDON_MAPPING_URL =\
    "https://s3-us-west-2.amazonaws.com/telemetry-public-analysis-2/telemetry-ml/addon_recommender/addon_mapping.json"

logger = logging.getLogger(__name__)


# http://garage.pimentech.net/libcommonPython_src_python_libcommon_javastringhashcode/
def java_string_hashcode(s):
    h = 0
    for c in s:
        h = (31 * h + ord(c)) & 0xFFFFFFFF
    return ((h + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def positive_hash(s):
    return java_string_hashcode(s) & 0x7FFFFF


class CollaborativeRecommender(AbstractRecommender):
    """ The addon recommendation interface to the collaborative filtering model.

    Usage example::

        recommender = CollaborativeRecommender()
        dists = recommender.recommend(client_info)
    """
    def __init__(self, ctx):
        self._ctx = ctx

        assert 'cache' in self._ctx

        self._load_json_models()
        self.model = None
        self._build_model()

    def _load_json_models(self):
        # Download the addon mappings.
        self.addon_mapping = self._ctx['cache'].fetch_json(ADDON_MAPPING_URL)
        if self.addon_mapping is None:
            logger.error("Cannot download the addon mapping file {}".format(ADDON_MAPPING_URL))

        self.raw_item_matrix = self._ctx['cache'].fetch_json(ADDON_MODEL_URL)
        if self.addon_mapping is None:
            logger.error("Cannot download the model file {}".format(ADDON_MODEL_URL))

    def _build_model(self):
        if self.raw_item_matrix is None:
            return

        # Build a dense numpy matrix out of it.
        num_rows = len(self.raw_item_matrix)
        num_cols = len(self.raw_item_matrix[0]['features'])

        self.model = np.zeros(shape=(num_rows, num_cols))
        for index, row in enumerate(self.raw_item_matrix):
            self.model[index, :] = row['features']

    def can_recommend(self, client_data, extra_data={}):
        # We can't recommend if we don't have our data files.
        if self.raw_item_matrix is None or self.model is None or self.addon_mapping is None:
            return False

        # We only get meaningful recommendation if a client has at least an
        # addon installed.
        if len(client_data.get('installed_addons', [])) > 0:
            return True

        return False

    def recommend(self, client_data, limit, extra_data={}):
        # Addons identifiers are stored as positive hash values within the model.
        installed_addons_as_hashes =\
            [positive_hash(addon_id) for addon_id in client_data.get('installed_addons', [])]

        # Build the query vector by setting the position of the queried addons to 1.0
        # and the other to 0.0.
        query_vector = np.array([1.0
                                 if (entry.get("id") in installed_addons_as_hashes)
                                 else 0.0 for entry in self.raw_item_matrix])

        # Build the user factors matrix.
        user_factors = np.matmul(query_vector, self.model)
        user_factors_transposed = np.transpose(user_factors)

        # Compute the distance between the user and all the addons in the latent
        # space.
        distances = {}
        for addon in self.raw_item_matrix:
            # We don't really need to show the items we requested.
            # They will always end up with the greatest score. Also
            # filter out legacy addons from the suggestions.
            hashed_id = addon.get("id")
            str_hashed_id = str(hashed_id)
            if (hashed_id in installed_addons_as_hashes or
                    str_hashed_id not in self.addon_mapping or
                    self.addon_mapping[str_hashed_id].get("isWebextension", False) is False):
                continue

            dist = np.dot(user_factors_transposed, addon.get('features'))
            # Read the addon ids from the "addon_mapping" looking it
            # up by 'id' (which is an hashed value).
            addon_id = self.addon_mapping[str_hashed_id].get("id")
            distances[addon_id] = dist

        # Sort the suggested addons by their score and return the
        # sorted list of addon ids.
        sorted_dists = sorted(distances.items(),
                              key=op.itemgetter(1),
                              reverse=True)
        return [(s[0], s[1]) for s in sorted_dists[:limit]]
