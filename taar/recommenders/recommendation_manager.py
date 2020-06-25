# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.ensemble_recommender import EnsembleRecommender
from srgutil.interfaces import IMozLogging

from taar.context import default_context

from .lazys3 import LazyJSONLoader
import random

from .s3config import TAAR_WHITELIST_BUCKET
from .s3config import TAAR_WHITELIST_KEY

import hashlib

# We need to build a default logger for the schema validation as there
# is no class to bind to yet.
ctx = default_context()


def hasher(client_id):
    return hashlib.new("sha256", client_id.encode("utf8")).hexdigest()


TEST_CLIENT_IDS = [
    hasher("00000000-0000-0000-0000-000000000000"),
    hasher("11111111-1111-1111-1111-111111111111"),
    hasher("22222222-2222-2222-2222-222222222222"),
    hasher("33333333-3333-3333-3333-333333333333"),
]

EMPTY_TEST_CLIENT_IDS = [
    hasher("00000000-aaaa-0000-0000-000000000000"),
    hasher("11111111-aaaa-1111-1111-111111111111"),
    hasher("22222222-aaaa-2222-2222-222222222222"),
    hasher("33333333-aaaa-3333-3333-333333333333"),
]


class RecommenderFactory:
    """
    A RecommenderFactory provides support to create recommenders.

    The existence of a factory enables injection of dependencies into
    the RecommendationManager and eases the implementation of test
    harnesses.
    """

    def __init__(self, ctx):
        self._ctx = ctx
        # This map is set in the default context
        self._recommender_factory_map = self._ctx["recommender_factory_map"]

    def get_names(self):
        return self._recommender_factory_map.keys()

    def create(self, recommender_name):
        return self._recommender_factory_map[recommender_name]()


class RecommendationManager:
    """This class determines which of the set of recommendation
    engines will actually be used to generate recommendations."""

    def __init__(self, ctx):
        """Initialize the user profile fetcher and the recommenders.
        """
        self._ctx = ctx
        self.logger = self._ctx[IMozLogging].get_logger("taar")

        assert "profile_fetcher" in self._ctx

        self.profile_fetcher = ctx["profile_fetcher"]

        self._ensemble_recommender = EnsembleRecommender(self._ctx.child())

        # The whitelist data is only used for test client IDs

        self._whitelist_data = LazyJSONLoader(
            self._ctx, TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY
        )

    def recommend(self, client_id, limit, extra_data={}):
        """Return recommendations for the given client.

        The recommendation logic will go through each recommender and
        pick the first one that "can_recommend".

        :param client_id: the client unique id.
        :param limit: the maximum number of recommendations to return.
        :param extra_data: a dictionary with extra client data.
        """

        if client_id in TEST_CLIENT_IDS:
            data = self._whitelist_data.get()[0]
            random.shuffle(data)
            samples = data[:limit]
            self.logger.info("Test ID detected [{}]".format(client_id))
            return [(s, 1.1) for s in samples]

        if client_id in EMPTY_TEST_CLIENT_IDS:
            self.logger.info("Empty Test ID detected [{}]".format(client_id))
            return []

        client_info = self.profile_fetcher.get(client_id)
        if client_info is None:
            self.logger.info(
                "Defaulting to empty results.  No client info fetched from storage backend."
            )
            return []

        results = self._ensemble_recommender.recommend(client_info, limit, extra_data)

        return results
