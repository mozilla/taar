# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.recommenders.ensemble_recommender import (
    EnsembleRecommender,
    is_test_client,
)
from taar.recommenders.randomizer import in_experiment, reorder_guids
from srgutil.interfaces import IMozLogging
from .lazys3 import LazyJSONLoader

from taar.settings import (
    TAAR_WHITELIST_BUCKET,
    TAAR_WHITELIST_KEY,
    TAAR_EXPERIMENT_PROB,
)

import markus


metrics = markus.get_metrics("taar")


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
            self._ctx, TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY, "whitelist"
        )

        self._experiment_prob = ctx.get("TAAR_EXPERIMENT_PROB", TAAR_EXPERIMENT_PROB)

    @metrics.timer_decorator("profile_recommendation")
    def recommend(self, client_id, limit, extra_data={}):
        """Return recommendations for the given client.

        The recommendation logic will go through each recommender and
        pick the first one that "can_recommend".

        :param client_id: the client unique id.
        :param limit: the maximum number of recommendations to return.
        :param extra_data: a dictionary with extra client data.
        """

        results = None

        if is_test_client(client_id):
            # Just create a stub client_info blob
            client_info = {
                "client_id": client_id,
            }
        else:
            client_info = self.profile_fetcher.get(client_id)
            if client_info is None:
                self.logger.info(
                    "Defaulting to empty results.  No client info fetched from storage backend."
                )
                return []

        if in_experiment(client_id, self._experiment_prob):
            if results is None:
                # Fetch back all possible whitelisted addons for this
                # client
                extra_data["guid_randomization"] = True
                whitelist = self._whitelist_data.get()[0]
                results = self._ensemble_recommender.recommend(
                    client_info, len(whitelist), extra_data
                )
            results = reorder_guids(results, limit)
        else:
            if results is None:
                results = self._ensemble_recommender.recommend(
                    client_info, limit, extra_data
                )

        return results
