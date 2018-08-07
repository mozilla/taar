# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from srgutil.interfaces import IMozLogging
from .base_recommender import AbstractRecommender
from .s3_data import CuratedWhitelistCache

S3_BUCKET = 'telemetry-parquet'
ENSEMBLE_WEIGHTS = 'taar/ensemble/ensemble_weight.json'


class CuratedRecommender(AbstractRecommender):
    """
    The curated recommender just delegates to the whitelist
    that is provided by the AMO team.

    This recommender simply provides a randomized sample of
    pre-approved addons for recommendation. It does not use any other
    external data to generate recommendations, nor does it use any
    information from the Firefox agent.
    """

    def __init__(self, ctx):
        self._ctx = ctx

        self.logger = self._ctx[IMozLogging].get_logger('taar')
        self._curated_wl = CuratedWhitelistCache(self._ctx)

    def can_recommend(self, client_data, extra_data={}):
        """The Curated recommender will always be able to recommend
        something"""
        return True

    def recommend(self, client_data, limit, extra_data={}):
        """
        Curated recommendations are just random selections
        """
        guids = self._curated_wl.get_randomized_guid_sample(limit)

        log_data = (client_data['client_id'], str(guids))
        self.logger.info("client_id: [%s], guids: [%s]" % log_data)

        results = [(guid, 1.0) for guid in guids]
        return results


class HybridRecommender(AbstractRecommender):
    """
    The EnsembleRecommender is a collection of recommenders where the
    results from each recommendation is amplified or dampened by a
    factor.  The aggregate results are combines and used to recommend
    addons for users.
    """
    def __init__(self, ctx):
        self._ctx = ctx

        self.logger = self._ctx[IMozLogging].get_logger('taar')

        self._ensemble_recommender = self._ctx['ensemble_recommender']
        self._curated_recommender = CuratedRecommender(self._ctx.child())

    def can_recommend(self, client_data, extra_data={}):
        """The ensemble recommender is always going to be
        available if at least one recommender is available"""
        ensemble_recommend = self._ensemble_recommender.can_recommend(client_data, extra_data)
        curated_recommend = self._curated_recommender.can_recommend(client_data, extra_data)
        return ensemble_recommend and curated_recommend

    def recommend(self, client_data, limit, extra_data={}):
        """
        Hybrid recommendations simply select half recommendations from
        the ensemble recommender, and half from the curated one.

        Duplicate recommendations are accomodated by rank ordering
        by weight.
        """

        preinstalled_addon_ids = client_data.get('installed_addons', [])

        # Compute an extended limit by adding the length of
        # the list of any preinstalled addons.
        extended_limit = limit + len(preinstalled_addon_ids)

        ensemble_weights = self._weight_cache.getWeights()

        ensemble_suggestions = self._ensemble_recommender.recommend(client_data,
                                                                    extended_limit,
                                                                    extra_data)
        curated_suggestions = self._curated_recommender.recommend(client_data,
                                                                  extended_limit,
                                                                  extra_data)

        # Generate a set of results from each of the composite
        # recommenders.  We select one item from each recommender
        # sequentially so that we do not bias one recommender over the
        # other.
        merged_results = set()
        while len(merged_results) < limit and len(ensemble_suggestions) > 0 and len(curated_suggestions) > 0:

            r1 = ensemble_suggestions.pop()
            if r1[0] not in [temp[0] for temp in merged_results]:
                merged_results.add(r1)

            r2 = curated_suggestions.pop()
            if r2[0] not in [temp[0] for temp in merged_results]:
                merged_results.add(r1)

        if len(merged_results) < limit:
            msg = "Insufficient recommendations found for client: %s" % client_data['client_id']
            self.logger.info(msg)
            return []

        log_data = (client_data['client_id'],
                    str(ensemble_weights),
                    str([r[0] for r in merged_results]))
        self.logger.info("client_id: [%s], ensemble_weight: [%s], guids: [%s]" % log_data)
        return list(merged_results)
