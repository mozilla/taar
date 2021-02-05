# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.


from taar.interfaces import IMozLogging, ITAARCache

import markus

from taar.recommenders.debug import log_timer_debug

metrics = markus.get_metrics("taar")


NORM_MODE_ROWNORMSUM = "rownorm_sum"
NORM_MODE_ROWCOUNT = "row_count"
NORM_MODE_ROWSUM = "row_sum"
NORM_MODE_GUIDCEPTION = "guidception"


class GuidBasedRecommender:
    """ A recommender class that returns top N addons based on a
    passed addon identifier.  This will load a json file containing
    updated top n addons coinstalled with the addon passed as an input
    parameter based on periodically updated  addon-addon
    coinstallation frequency table generated from  Longitdudinal
    Telemetry data.  This recommender will drive recommendations
    surfaced on addons.mozilla.org


    We store the JSON data for the GUID coinstallation in memory. This
    consumes ~ 15.8MB of heap.

        In [10]: from pympler import asizeof

        In [11]: jdata = json.load(open('guid_coinstallation.json'))

        In [12]: asizeof.asizeof(jdata)
        Out[12]: 15784672

    Each of the data normalization dictionaries is also stored in
    memory.
    """

    _addons_coinstallations = None
    _guid_maps = {}

    # Define recursion levels for guid-ception
    RECURSION_LEVELS = 3

    def __init__(self, ctx):
        self._ctx = ctx
        self.logger = self._ctx[IMozLogging].get_logger("taarlite")

        self._cache = ctx[ITAARCache]
        self.logger.info("GUIDBasedRecommender is initialized")

    def cache_ready(self):
        return self._cache.is_active()

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if not self._cache.is_active():
            return False

        # If we have data coming from other sources, we can use that for
        # recommending.
        addon_guid = client_data.get("guid", None)
        if not isinstance(addon_guid, str):
            return False

        # Use a dictionary keyed on the query guid
        if not self._cache.has_coinstalls_for(addon_guid):
            return False

        if not self._cache.get_coinstalls(addon_guid):
            return False

        return True

    @metrics.timer_decorator("guid_recommendation")
    def recommend(self, client_data, limit=4):
        """
        TAAR lite will yield 4 recommendations for the AMO page
        """

        if not self._cache.is_active():
            return []

        with log_timer_debug(f"Results computed", self.logger):

            with log_timer_debug("get client data", self.logger):
                addon_guid = client_data.get("guid")

            # Get the raw co-installation result dictionary
            with log_timer_debug("Get filtered coinstallations", self.logger):
                result_dict = self._cache.get_filtered_coinstall(addon_guid, {})

            with log_timer_debug("acquire normalization method", self.logger):
                normalize = client_data.get("normalize", NORM_MODE_ROWNORMSUM)

                norm_dict = {
                    "none": lambda guid, x: x,
                    NORM_MODE_ROWCOUNT: self.norm_row_count,
                    NORM_MODE_ROWSUM: self.norm_row_sum,
                    NORM_MODE_ROWNORMSUM: self.norm_rownorm_sum,
                    NORM_MODE_GUIDCEPTION: self.norm_guidception,
                }

                if normalize is not None and normalize not in norm_dict.keys():
                    # Yield no results if the normalization method is not
                    # specified
                    self.logger.warning(
                        "Invalid normalization parameter detected: [%s]" % normalize
                    )
                    return []

                # Bind the normalization method
                norm_method = norm_dict[normalize]

            with log_timer_debug(
                f"Compute normalization using method:{normalize}", self.logger
            ):
                # Apply normalization
                tmp_result_dict = norm_method(addon_guid, result_dict)

            # Augment the result_dict with the installation counts
            # and then we can sort using lexical sorting of strings.
            # The idea here is to get something in the form of
            #    0000.0000.0000
            # The computed weight takes the first and second segments of
            # integers.  The third segment is the installation count of
            # the addon but is zero padded.

            TWICE_LIMIT = limit * 2
            with log_timer_debug(
                f"Augment {TWICE_LIMIT} with installation counts and resorted",
                self.logger,
            ):
                result_list = []
                rank_sorted = sorted(
                    tmp_result_dict.items(), key=lambda x: x[1], reverse=True
                )
                for k, v in rank_sorted[:TWICE_LIMIT]:
                    lex_value = "{0:020.10f}.{1:010d}".format(
                        v, self._cache.get_rankings(k, 0)
                    )
                    result_list.append((k, lex_value))

                # Sort the result list in descending order by weight
                result_list.sort(key=lambda x: x[1], reverse=True)

            self.logger.info(
                "Addon related recommendations results",
                extra={'guid': str(addon_guid), 'recs': [str(r[0]) for r in result_list[:limit]]}
            )

        return result_list[:limit]

    def norm_row_count(self, key_guid, input_coinstall_dict):
        """This normalization method counts the unique times that a
        GUID is coinstalled with any other GUID.

        This dampens weight of any suggested GUID inversely
        proportional to it's overall popularity.
        """

        output_result_dict = {}
        for result_guid, result_count in input_coinstall_dict.items():
            output_result_dict[result_guid] = (
                1.0 * result_count / self._cache.guid_maps_rowcount(result_guid)
            )
        return output_result_dict

    def norm_row_sum(self, key_guid, input_coinstall_dict):
        """This normalization normalizes the weights for the suggested
        coinstallation GUIDs based on the sum of the weights for the
        coinstallation GUIDs given a key GUID.
        """

        def generate_row_sum_list():
            for guid, guid_weight in input_coinstall_dict.items():
                norm_guid_weight = (
                    guid_weight * 1.0 / self._cache.guid_maps_count_map(guid)
                )

                yield guid, norm_guid_weight

        return dict(generate_row_sum_list())

    def norm_rownorm_sum(self, key_guid, input_coinstall_dict):
        """This normalization is the same as norm_row_sum, but we also
        divide the result by the sum of
        (addon coinstall instances)/(addon coinstall total instances)

        The testcase for this scenario lays out the math more
        explicitly.
        """
        with log_timer_debug("normalize row weights for coinstall dict", self.logger):
            tmp_dict = self._normalize_row_weights(input_coinstall_dict)

        with log_timer_debug(
            f"normalizing output_dict of size: {len(tmp_dict)}", self.logger
        ):
            output_dict = {}
            for output_guid, output_guid_weight in tmp_dict.items():
                guid_row_norm_list = self._cache.guid_maps_row_norm(
                    output_guid, []
                )
                if len(guid_row_norm_list) == 0:
                    self.logger.warning(
                        "Can't find GUID_ROW_NORM data for [{}]".format(output_guid)
                    )
                    continue
                norm_sum = sum(guid_row_norm_list)
                if norm_sum == 0:
                    self.logger.warning(
                        "Sum of GUID_ROW_NORM data for [{}] is zero.".format(
                            output_guid
                        )
                    )
                    continue
                output_dict[output_guid] = output_guid_weight / norm_sum

        return output_dict

    def norm_guidception(self, key_guid, input_coinstall_dict):
        tmp_dict = self._normalize_row_weights(input_coinstall_dict)

        return self._compute_recursive_results(tmp_dict, self.RECURSION_LEVELS)

    def _normalize_row_weights(self, coinstall_dict):
        # Compute an intermediary dictionary that is a row normalized
        # co-install. That is - each coinstalled guid weight is
        # divided by the sum of the weights for all coinstalled guids
        # on this row.
        tmp_dict = {}
        coinstall_total_weight = sum(coinstall_dict.values())
        for coinstall_guid, coinstall_weight in coinstall_dict.items():
            tmp_dict[coinstall_guid] = coinstall_weight / coinstall_total_weight
        return tmp_dict

    def _recursion_penalty(self, level):
        """ Return a factor to apply to the weight for a guid
        recommendation.
        """
        dampener = 1.0 - (1.0 * (self.RECURSION_LEVELS - level) / self.RECURSION_LEVELS)
        dampener *= dampener
        return dampener

    def _compute_recursive_results(self, row_normalized_coinstall, level):
        if level <= 0:
            return row_normalized_coinstall

        # consolidated_coinstall_dict will capture values
        consolidated_coinstall_dict = {}

        # Add this level's guid weight to the consolidated result
        dampener = self._recursion_penalty(level)
        for (
            recommendation_guid,
            recommendation_guid_weight,
        ) in row_normalized_coinstall.items():
            for guid, guid_weight in row_normalized_coinstall.items():
                weight = consolidated_coinstall_dict.get(guid, 0)
                weight += dampener * guid_weight
                consolidated_coinstall_dict[guid] = weight

        # Add in the next level
        level -= 1
        for guid in consolidated_coinstall_dict.keys():
            next_level_coinstalls = self._cache.get_coinstalls(guid, {})
            if next_level_coinstalls != {}:
                # Normalize the next bunch of suggestions
                next_level_coinstalls = self._normalize_row_weights(
                    next_level_coinstalls
                )

                next_level_results = self._compute_recursive_results(
                    next_level_coinstalls, level
                )
                for (next_level_guid, next_level_weight,) in next_level_results.items():
                    weight = consolidated_coinstall_dict.get(guid, 0)
                    weight += next_level_weight
                    consolidated_coinstall_dict[guid] = weight

        # normalize the final results
        return self._normalize_row_weights(consolidated_coinstall_dict)
