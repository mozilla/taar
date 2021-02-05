# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.interfaces import IMozLogging, ITAARCache
import numpy as np
import operator as op

from taar.recommenders.base_recommender import AbstractRecommender


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

        self.logger = self._ctx[IMozLogging].get_logger("taar")

        self._cache = self._ctx[ITAARCache]

    def _get_cache(self, extra_data):
        tmp = extra_data.get("cache", None)
        if tmp is None:
            tmp = self._cache.cache_context()
        return tmp

    def can_recommend(self, client_data, extra_data={}):
        cache = self._get_cache(extra_data)
        # We can't recommend if we don't have our data files.
        if (
                cache["raw_item_matrix"] is None
                or cache["collab_model"] is None
                or cache["addon_mapping"] is None
        ):
            return False

        # We only get meaningful recommendation if a client has at least an
        # addon installed.
        if len(client_data.get("installed_addons", [])) > 0:
            return True

        return False

    def _recommend(self, client_data, limit, extra_data):
        cache = self._get_cache(extra_data)

        installed_addons_as_hashes = [
            positive_hash(addon_id)
            for addon_id in client_data.get("installed_addons", [])
        ]

        # Build the query vector by setting the position of the queried addons to 1.0
        # and the other to 0.0.
        query_vector = np.array(
            [
                1.0 if (entry.get("id") in installed_addons_as_hashes) else 0.0
                for entry in cache["raw_item_matrix"]
            ]
        )

        # Build the user factors matrix.
        user_factors = np.matmul(query_vector, cache["collab_model"])
        user_factors_transposed = np.transpose(user_factors)

        # Compute the distance between the user and all the addons in the latent
        # space.
        distances = {}
        for addon in cache["raw_item_matrix"]:
            # We don't really need to show the items we requested.
            # They will always end up with the greatest score. Also
            # filter out legacy addons from the suggestions.
            hashed_id = addon.get("id")
            str_hashed_id = str(hashed_id)
            if (
                    hashed_id in installed_addons_as_hashes
                    or str_hashed_id not in cache["addon_mapping"]
                    or cache["addon_mapping"][str_hashed_id].get("isWebextension", False)
                    is False
            ):
                continue

            dist = np.dot(user_factors_transposed, addon.get("features"))
            # Read the addon ids from the "addon_mapping" looking it
            # up by 'id' (which is an hashed value).
            addon_id = cache["addon_mapping"][str_hashed_id].get("id")
            distances[addon_id] = dist

        # Sort the suggested addons by their score and return the
        # sorted list of addon ids.
        sorted_dists = sorted(distances.items(), key=op.itemgetter(1), reverse=True)
        recommendations = [(s[0], s[1]) for s in sorted_dists[:limit]]
        return recommendations

    def recommend(self, client_data, limit, extra_data={}):
        # Addons identifiers are stored as positive hash values within the model.

        recommendations = self._recommend(client_data, limit, extra_data)

        log_data = (
            client_data["client_id"],
            str([r[0] for r in recommendations]),
        )
        self.logger.debug(
            "collaborative_recommender_triggered, "
            "client_id: [%s], "
            "guids: [%s]" % log_data
        )

        return recommendations
