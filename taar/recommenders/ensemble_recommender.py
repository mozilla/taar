# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import itertools
from .base_recommender import AbstractRecommender
import threading
import time

S3_BUCKET = 'telemetry-parquet'
ENSEMBLE_WEIGHTS = 'taar/ensemble/ensemble_weight.json'

logger = logging.getLogger(__name__)


class WeightCache:
    def __init__(self, ctx):
        self._ctx = ctx
        assert 'cache' in self._ctx

        self._lock = threading.RLock()

        self._weights = None
        self._expiry = None

    def now(self):
        return time.time()

    def getWeights(self):
        with self._lock:
            now = self.now()
            if self._expiry is not None:
                if self._expiry < now:
                    # Cache is expired.
                    self._weights = None
                    # Push expiry to 5 minutes from now
                    self._expiry = now + 300

            if self._weights is None:
                tmp = self._ctx['cache'].get_s3_json_content(S3_BUCKET, ENSEMBLE_WEIGHTS)
                self._weights = tmp['ensemble_weights']

            return self._weights


class EnsembleRecommender(AbstractRecommender):
    """
    The EnsembleRecommender is a collection of recommenders where the
    results from each recommendation is amplified or dampened by a
    factor.  The aggregate results are combines and used to recommend
    addons for users.
    """
    def __init__(self, ctx):
        self._ctx = ctx

        assert 'recommender_map' in self._ctx

        self._init_from_ctx()

    def _init_from_ctx(self):
        # Copy the map of the recommenders
        self.RECOMMENDER_KEYS = ['collaborative', 'similarity', 'locale']
        self._recommender_map = self._ctx['recommender_map']
        self._weight_cache = WeightCache(self._ctx.child())

    def can_recommend(self, client_data, extra_data={}):
        """The ensemble recommender is always going to be
        available if at least one recommender is available"""
        return sum([self._recommender_map[rkey].can_recommend(client_data)
                    for rkey in self.RECOMMENDER_KEYS])

    def recommend(self, client_data, limit, extra_data={}):
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

        preinstalled_addon_ids = client_data.get('installed_addons', [])

        # Compute an extended limit by adding the length of
        # the list of any preinstalled addons.
        extended_limit = limit + len(preinstalled_addon_ids)

        flattened_results = []
        ensemble_weights = self._weight_cache.getWeights()

        for rkey in self.RECOMMENDER_KEYS:
            recommender = self._recommender_map[rkey]

            if recommender.can_recommend(client_data):
                raw_results = recommender.recommend(client_data,
                                                    extended_limit,
                                                    extra_data)
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

        filtered_ensemble_suggestions = [(guid, weight) for (guid, weight)
                                         in ensemble_suggestions
                                         if guid not in preinstalled_addon_ids]

        results = filtered_ensemble_suggestions[:limit]

        log_data = (client_data['client_id'],
                    str(ensemble_weights),
                    str([r[0] for r in results]))
        logger.info("client_id: [%s], ensemble_weight: [%s], guids: [%s]" % log_data)
        return results
