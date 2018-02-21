# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import itertools
from ..recommenders import utils
from .base_recommender import BaseRecommender

S3_BUCKET = 'telemetry-parquet'
ENSEMBLE_WEIGHTS = 'taar/ensemble/ensemble_weight.json'

logger = logging.getLogger(__name__)


class EnsembleRecommender(BaseRecommender):
    """
    The EnsembleRecommender is a collection of recommenders where the
    results from each recommendation is amplified or dampened by a
    factor.  The aggregate results are combines and used to recommend
    addons for users.
    """
    def __init__(self, recommender_map):
        tmp = utils.get_s3_json_content(S3_BUCKET, ENSEMBLE_WEIGHTS)
        self._ensemble_weights = tmp['ensemble_weights']

        # Copy the map of the recommenders

        self.RECOMMENDER_KEYS = ['legacy', 'collaborative', 'similarity', 'locale']
        self._recommender_map = recommender_map

    def can_recommend(self, client_data, extra_data={}):
        """The ensemble recommender is always going to be
        available"""
        return True

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
        flattened_results = []
        for rkey in self.RECOMMENDER_KEYS:
            recommender = self._recommender_map[rkey]

            if recommender.can_recommend(client_data):
                raw_results = recommender.recommend(client_data, limit, extra_data)

                reweighted_results = []
                for guid, weight in raw_results:
                    item = (guid, weight * self._ensemble_weights[rkey])
                    reweighted_results.append(item)
                flattened_results.extend(reweighted_results)

        # Sort the results by the GUID
        flattened_results.sort(lambda item: item[0])

        # group by the guid, sum up the weights for recurring GUID
        # suggestions across all recommenders
        guid_grouper = itertools.groupby(flattened_results, lambda item: item[0])

        ensemble_suggestions = []
        for (guid, guid_group) in guid_grouper:
            weight_sum = sum([v for (g, v) in guid_group])
            item = (guid, weight_sum)
            ensemble_suggestions.append(item)

        # Sort in reverse order (greatest weight to least)
        ensemble_suggestions.sort(lambda x: -x[1])
        results = ensemble_suggestions[:limit]
        return results
