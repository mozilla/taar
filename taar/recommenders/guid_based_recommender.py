# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np

from .lazys3 import LazyJSONLoader
from srgutil.interfaces import IMozLogging

import markus


from taar.settings import (
    TAARLITE_GUID_COINSTALL_BUCKET,
    TAARLITE_GUID_COINSTALL_KEY,
    TAARLITE_GUID_RANKING_KEY,
)


metrics = markus.get_metrics("taar")

ADDON_DL_ERR = (
    f"Cannot download addon coinstallation file {TAARLITE_GUID_COINSTALL_KEY}"
)

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

        if "coinstall_loader" in self._ctx:
            self._addons_coinstall_loader = self._ctx["coinstall_loader"]
        else:
            self._addons_coinstall_loader = LazyJSONLoader(
                self._ctx,
                TAARLITE_GUID_COINSTALL_BUCKET,
                TAARLITE_GUID_COINSTALL_KEY,
                "guid_coinstall",
            )

        if "ranking_loader" in self._ctx:
            self._guid_ranking_loader = self._ctx["ranking_loader"]
        else:
            self._guid_ranking_loader = LazyJSONLoader(
                self._ctx,
                TAARLITE_GUID_COINSTALL_BUCKET,
                TAARLITE_GUID_RANKING_KEY,
                "guid_ranking",
            )

        self._init_from_ctx()

        # Force access to the JSON models for each request at
        # recommender construction.  This was lifted out of the
        # constructor for the LazyJSONLoader so that the
        # precomputation of the normalization tables can be done in
        # the recommender.
        _ = self._addons_coinstallations  # noqa
        _ = self._guid_rankings  # noqa

        self.logger.info("GUIDBasedRecommender is initialized")

    def _init_from_ctx(self):
        self.logger = self._ctx[IMozLogging].get_logger("taarlite")

        if self._addons_coinstallations is None:
            self.logger.error(ADDON_DL_ERR)

        # Compute the floor install incidence that recommended addons
        # must satisfy.  Take 5% of the mean of all installed addons.
        self._min_installs = np.mean(list(self._guid_rankings.values())) * 0.05

        # Warn if the minimum number of installs drops below 100.
        if self._min_installs < 100:
            self.logger.warning(
                "minimum installs threshold low: [%s]" % self._min_installs
            )

    @property
    def _addons_coinstallations(self):
        result, refreshed = self._addons_coinstall_loader.get()
        if refreshed:
            self.logger.info("Refreshing guid_maps for normalization")
            self._precompute_normalization()
        return result

    @property
    def _guid_rankings(self):
        result, refreshed = self._guid_ranking_loader.get()
        if refreshed:
            self.logger.info("Refreshing guid_maps for normalization")
            self._precompute_normalization()
        return result

    def _precompute_normalization(self):
        if self._addons_coinstallations is None:
            self.logger.error("Cannot find addon coinstallations to normalize.")
            return

        # Capture the total number of times that a guid was
        # coinstalled with another GUID
        #
        # This is a map is guid->sum of coinstall counts
        guid_count_map = {}

        # Capture the number of times a GUID shows up per row
        # of coinstallation data.
        #
        # This is a map of guid->rows that this guid appears on
        row_count = {}

        guid_row_norm = {}

        for guidkey, coinstalls in self._addons_coinstallations.items():
            rowsum = sum(coinstalls.values())
            for coinstall_guid, coinstall_count in coinstalls.items():

                # Capture the total number of time a GUID was
                # coinstalled with other guids
                guid_count_map.setdefault(coinstall_guid, 0)
                guid_count_map[coinstall_guid] += coinstall_count

                # Capture the unique number of times a GUID is
                # coinstalled with other guids
                row_count.setdefault(coinstall_guid, 0)
                row_count[coinstall_guid] += 1

                if coinstall_guid not in guid_row_norm:
                    guid_row_norm[coinstall_guid] = []
                guid_row_norm[coinstall_guid].append(1.0 * coinstall_count / rowsum)

        self._guid_maps = {
            "count_map": guid_count_map,
            "row_count": row_count,
            "guid_row_norm": guid_row_norm,
        }

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self._addons_coinstallations is None:
            return False

        # If we have data coming from other sources, we can use that for
        # recommending.
        addon_guid = client_data.get("guid", None)
        if not isinstance(addon_guid, str):
            return False

        # Use a dictionary keyed on the query guid
        if addon_guid not in self._addons_coinstallations.keys():
            return False

        if not self._addons_coinstallations.get(addon_guid):
            return False

        return True

    @metrics.timer_decorator("guid_recommendation")
    def recommend(self, client_data, limit=4):
        """
        TAAR lite will yield 4 recommendations for the AMO page
        """

        # Force access to the JSON models for each request at the
        # start of the request to update normalization tables if
        # required.
        _ = self._addons_coinstallations  # noqa
        _ = self._guid_rankings  # noqa

        addon_guid = client_data.get("guid")

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

        # Get the raw co-installation result dictionary
        result_dict = self._addons_coinstallations.get(addon_guid, {})

        # Collect addon GUIDs where the install incidence is below a
        # floor incidence.
        removal_keys = []
        for k, v in result_dict.items():
            if self._guid_rankings.get(k, 0) < self._min_installs:
                removal_keys.append(k)

        # Remove the collected addons that are not installed enough
        for k in removal_keys:
            del result_dict[k]

        # Apply normalization
        tmp_result_dict = norm_method(addon_guid, result_dict)

        # Augment the result_dict with the installation counts
        # and then we can sort using lexical sorting of strings.
        # The idea here is to get something in the form of
        #    0000.0000.0000
        # The computed weight takes the first and second segments of
        # integers.  The third segment is the installation count of
        # the addon but is zero padded.
        result_dict = {}
        for k, v in tmp_result_dict.items():
            lex_value = "{0:020.10f}.{1:010d}".format(v, self._guid_rankings.get(k, 0))
            result_dict[k] = lex_value

        # Sort the result dictionary in descending order by weight
        result_list = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)

        log_data = (str(addon_guid), [str(r) for r in result_list[:limit]])
        self.logger.info(
            "Addon: [%s] triggered these recommendation guids: [%s]" % log_data
        )

        return result_list[:limit]

    def norm_row_count(self, key_guid, input_coinstall_dict):
        """This normalization method counts the unique times that a
        GUID is coinstalled with any other GUID.

        This dampens weight of any suggested GUID inversely
        proportional to it's overall popularity.
        """
        uniq_guid_map = self._guid_maps["row_count"]

        output_result_dict = {}
        for result_guid, result_count in input_coinstall_dict.items():
            output_result_dict[result_guid] = (
                1.0 * result_count / uniq_guid_map[result_guid]
            )
        return output_result_dict

    def norm_row_sum(self, key_guid, input_coinstall_dict):
        """This normalization normalizes the weights for the suggested
        coinstallation GUIDs based on the sum of the weights for the
        coinstallation GUIDs given a key GUID.
        """
        guid_count_map = self._guid_maps["count_map"]

        def generate_row_sum_list():
            for guid, guid_weight in input_coinstall_dict.items():
                norm_guid_weight = guid_weight * 1.0 / guid_count_map[guid]
                yield guid, norm_guid_weight

        return dict(generate_row_sum_list())

    def norm_rownorm_sum(self, key_guid, input_coinstall_dict):
        """This normalization is the same as norm_row_sum, but we also
        divide the result by the sum of
        (addon coinstall instances)/(addon coinstall total instances)

        The testcase for this scenario lays out the math more
        explicitly.
        """
        tmp_dict = self._normalize_row_weights(input_coinstall_dict)
        guid_row_norm = self._guid_maps["guid_row_norm"]

        output_dict = {}
        for output_guid, output_guid_weight in tmp_dict.items():
            guid_row_norm_list = guid_row_norm.get(output_guid, [])
            if len(guid_row_norm_list) == 0:
                self.logger.warning(
                    "Can't find GUID_ROW_NORM data for [{}]".format(output_guid)
                )
                continue
            norm_sum = sum(guid_row_norm_list)
            if norm_sum == 0:
                self.logger.warning(
                    "Sum of GUID_ROW_NORM data for [{}] is zero.".format(output_guid)
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
            next_level_coinstalls = self._addons_coinstallations.get(guid, {})
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
