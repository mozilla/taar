# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from srgutil.interfaces import IMozLogging
import itertools
from .base_recommender import AbstractRecommender
from srgutil.cache import LazyJSONLoader

from .s3config import TAAR_WHITELIST_BUCKET
from .s3config import TAAR_WHITELIST_KEY
from .s3config import TAAR_ENSEMBLE_BUCKET
from .s3config import TAAR_ENSEMBLE_KEY

from .fixtures import TEST_CLIENT_IDS, EMPTY_TEST_CLIENT_IDS, hasher


class WeightCache:
    def __init__(self, ctx):
        self._ctx = ctx

        self._weights = LazyJSONLoader(
            self._ctx, TAAR_ENSEMBLE_BUCKET, TAAR_ENSEMBLE_KEY
        )

    def getWeights(self):
        return self._weights.get()[0]["ensemble_weights"]


class EnsembleRecommender(AbstractRecommender):
    """
    The EnsembleRecommender is a collection of recommenders where the
    results from each recommendation is amplified or dampened by a
    factor.  The aggregate results are combines and used to recommend
    addons for users.
    """

    def __init__(self, ctx):
        self.RECOMMENDER_KEYS = ["collaborative", "similarity", "locale"]
        self._ctx = ctx
        self.logger = self._ctx.get(IMozLogging).get_logger("taar.ensemble")

        assert self._ctx.get("recommender_factory", None) is not None

        self._init_from_ctx()

    def _init_from_ctx(self):
        # Copy the map of the recommenders
        self._recommender_map = {}

        recommender_factory = self._ctx.get("recommender_factory")
        for rkey in self.RECOMMENDER_KEYS:
            self._recommender_map[rkey] = recommender_factory.create(rkey)

        self._whitelist_data = LazyJSONLoader(
            self._ctx, TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY
        )

        self._weight_cache = WeightCache(self._ctx)
        self.logger.info("EnsembleRecommender initialized")

    def can_recommend(self, client_data, extra_data={}):
        """The ensemble recommender is always going to be
        available if at least one recommender is available"""
        result = sum(
            [
                self._recommender_map[rkey].can_recommend(client_data)
                for rkey in self.RECOMMENDER_KEYS
            ]
        )
        self.logger.info("Ensemble can_recommend: {}".format(result))
        return result

    def recommend(self, client_data, limit, extra_data={}):
        client_id = client_data.get("client_id", "no-client-id")

        if client_id in TEST_CLIENT_IDS:
            whitelist = self._whitelist_data.get()[0]
            samples = whitelist[:limit]
            self.logger.info("Test ID detected [{}]".format(client_id))

            # Compute a stable weight for any whitelisted addon based
            # on the sha256 hash of the GUID
            p = [(int(hasher(s), 16) % 100) / 100.0 for s in samples]
            results = list(zip(samples, p))
        elif client_id in EMPTY_TEST_CLIENT_IDS:
            self.logger.info("Empty Test ID detected [{}]".format(client_id))
            results = []
        else:
            try:
                results = self._recommend(client_data, limit, extra_data)
            except Exception as e:
                results = []
                self._weight_cache._weights.force_expiry()
                self.logger.exception(
                    "Ensemble recommender crashed for {}".format(client_id), e
                )
        return results

    def _recommend(self, client_data, limit, extra_data={}):
        """
        Ensemble recommendations are aggregated from individual
        recommenders.  The ensemble recommender applies a weight to
        the recommendation outputs of each recommender to reorder the
        recommendations to be a better fit.

        The intuitive understanding is that the total space of
        recommended addons across all recommenders will include the
        'true' addons that should be recommended better than any
        individual recommender.  The ensemble method simply needs to
        weight each recommender appropriate so that the ordering is
        correct.
        """
        self.logger.info("Ensemble recommend invoked")
        preinstalled_addon_ids = client_data.get("installed_addons", [])

        # Compute an extended limit by adding the length of
        # the list of any preinstalled addons.
        extended_limit = limit + len(preinstalled_addon_ids)

        flattened_results = []
        ensemble_weights = self._weight_cache.getWeights()

        for rkey in self.RECOMMENDER_KEYS:
            recommender = self._recommender_map[rkey]

            if recommender.can_recommend(client_data):
                raw_results = recommender.recommend(
                    client_data, extended_limit, extra_data
                )
                reweighted_results = []
                for guid, weight in raw_results:
                    item = (guid, weight * ensemble_weights[rkey])
                    reweighted_results.append(item)
                flattened_results.extend(reweighted_results)

        # Sort the results by the GUID
        flattened_results.sort(key=lambda item: item[0])

        # group by the guid, sum up the weights for recurring GUID
        # suggestions across all recommenders
        guid_grouper = itertools.groupby(flattened_results, lambda item: item[0])

        ensemble_suggestions = []
        for (guid, guid_group) in guid_grouper:
            weight_sum = sum([v for (g, v) in guid_group])
            item = (guid, weight_sum)
            ensemble_suggestions.append(item)

        # Sort in reverse order (greatest weight to least)
        ensemble_suggestions.sort(key=lambda x: -x[1])

        filtered_ensemble_suggestions = [
            (guid, weight)
            for (guid, weight) in ensemble_suggestions
            if guid not in preinstalled_addon_ids
        ]

        results = filtered_ensemble_suggestions[:limit]

        log_data = (
            client_data["client_id"],
            extra_data.get("guid_randomization", False),
            str(ensemble_weights),
            str([r[0] for r in results]),
        )
        self.logger.info(
            "client_id: [%s], guid_randomization: [%s], ensemble_weight: [%s], guids: [%s]"
            % log_data
        )
        return results
