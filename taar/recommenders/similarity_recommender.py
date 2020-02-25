# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .base_recommender import AbstractRecommender
from itertools import groupby
from scipy.spatial import distance
from srgutil.log import get_logger
import numpy as np
from srgutil.cache import LazyJSONLoader

from .s3config import TAAR_SIMILARITY_BUCKET
from .s3config import TAAR_SIMILARITY_DONOR_KEY
from .s3config import TAAR_SIMILARITY_LRCURVES_KEY


FLOOR_DISTANCE_ADJUSTMENT = 0.001

CATEGORICAL_FEATURES = ["geo_city", "locale", "os"]
CONTINUOUS_FEATURES = [
    "subsession_length",
    "bookmark_count",
    "tab_open_count",
    "total_uri",
    "unique_tlds",
]


class SimilarityRecommender(AbstractRecommender):
    """ A recommender class that returns top N addons based on the
    client similarity with a set of candidate addon donors.

    Several telemetry fields are used to compute pairwise similarity
    with the donors and similarities are converted into a likelihood
    ratio of being a good match versus not being a good match. These
    quantities are then used to rank specific addons for
    recommendation.

    This will load a json file containing updated list of addon donors
    updated periodically by a separate weekly process using
    Longitdudinal Telemetry data.

    This recommender may provide useful recommendations when
    collaborative_recommender may not work.
    """

    def __init__(self, ctx):
        self._ctx = ctx

        if self._ctx.get("similarity_donors_pool", None) is not None:
            self._donors_pool = self._ctx.get("similarity_donors_pool")
        else:
            self._donors_pool = LazyJSONLoader(
                self._ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY
            )

        if self._ctx.get("similarity_lr_curves", None) is not None:
            self._lr_curves = self._ctx.get("similarity_lr_curves")
        else:
            self._lr_curves = LazyJSONLoader(
                self._ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY
            )

        self.logger = get_logger("taar")

        self._init_from_ctx()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["logger"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.logger = get_logger("taar")
        return state

    @property
    def donors_pool(self):
        result, status = self._donors_pool.get()
        if status:
            # Force a reconstruction of the features cache on new
            # donor pool data
            self._build_features_caches()
        return result

    @property
    def lr_curves(self):
        result, status = self._lr_curves.get()
        if status:
            # Force a reconstruction of the features cache on new
            # curve data
            self._build_features_caches()
        return result

    def _init_from_ctx(self):
        # Download the addon donors list.
        if self.donors_pool is None:
            self.logger.info(
                "Similarity donors pool has not been fetched from S3: {}".format(
                    TAAR_SIMILARITY_DONOR_KEY
                )
            )

        # Download the probability mapping curves from similarity to likelihood of being a good donor.
        if self.lr_curves is None:
            self.logger.error(
                "Similarity LR Curves have not been fetched from S3: {}".format(
                    TAAR_SIMILARITY_LRCURVES_KEY
                )
            )

    def _build_features_caches(self):
        """This function build two feature cache matrices.

        That's the self.categorical_features and
        self.continuous_features attributes.

        One matrix is for the continuous features and the other is for
        the categorical features. This is needed to speed up the similarity
        recommendation process."""
        _donors_pool = self._donors_pool.get()[0]
        _lr_curves = self._lr_curves.get()[0]

        if _donors_pool is None or _lr_curves is None:
            # We need to have both donors_pool and lr_curves defined
            # to reconstruct the matrices
            return None

        self.num_donors = len(_donors_pool)

        # Build a numpy matrix cache for the continuous features.
        self.continuous_features = np.zeros(
            (self.num_donors, len(CONTINUOUS_FEATURES))
        )
        for idx, d in enumerate(_donors_pool):
            features = [
                d.get(specified_key) for specified_key in CONTINUOUS_FEATURES
            ]
            self.continuous_features[idx] = features

        # Build the cache for categorical features.
        self.categorical_features = np.zeros(
            (self.num_donors, len(CATEGORICAL_FEATURES)), dtype="object"
        )
        for idx, d in enumerate(_donors_pool):
            features = [
                d.get(specified_key) for specified_key in CATEGORICAL_FEATURES
            ]
            self.categorical_features[idx] = np.array(
                [features], dtype="object"
            )

        self.logger.info("Reconstructed matrices for similarity recommender")

    def can_recommend(self, client_data, extra_data={}):
        # We can't recommend if we don't have our data files.
        if self.donors_pool is None or self.lr_curves is None:
            return False

        # Check that the client info contains a non-None value for each required
        # telemetry field.
        REQUIRED_FIELDS = CATEGORICAL_FEATURES + CONTINUOUS_FEATURES

        has_fields = all(
            [client_data.get(f, None) is not None for f in REQUIRED_FIELDS]
        )
        if not has_fields:
            # Can not add extra info because client_id may not be available.
            self.logger.error("Unusable client data encountered")
        return has_fields

    def get_lr(self, score):
        """Compute a :float: likelihood ratio from a provided similarity score when compared
        to two probability density functions which are computed and pre-loaded during init.

        The numerator indicates the probability density that a particular similarity score
        corresponds to a 'good' addon donor, i.e. a client that is similar in the sense of
        telemetry variables. The denominator indicates the probability density that a particular
        similarity score corresponds to a 'poor' addon donor

        :param score: A similarity score between a pair of objects.
        :returns: The approximate float likelihood ratio corresponding to provided score.
        """
        # Find the index of the closest value that was precomputed in lr_curves
        # This will significantly speed up |get_lr|.

        # The lr_curves_cache is a list of scalar distance
        # measurements
        lr_curves_cache = np.array([s[0] for s in self.lr_curves])

        # np.argmin produces the index to the part of the curve
        # where distance is the smallest to the score which we are
        # inspecting currently.
        idx = np.argmin(abs(score - lr_curves_cache))

        numer_val = self.lr_curves[idx][1][0]
        denum_val = self.lr_curves[idx][1][1]

        # Compute LR based on numerator and denominator values
        return float(numer_val) / float(denum_val)

    # # # CAUTION! # # #
    # Any changes to this function must be reflected in the corresponding ETL job.
    # https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_similarity.py
    #
    def compute_clients_dist(self, client_data):
        client_categorical_feats = [
            client_data.get(specified_key)
            for specified_key in CATEGORICAL_FEATURES
        ]
        client_continuous_feats = [
            client_data.get(specified_key)
            for specified_key in CONTINUOUS_FEATURES
        ]

        # Compute the distances between the user and the cached continuous features.
        cont_features = distance.cdist(
            self.continuous_features,
            np.array([client_continuous_feats]),
            "canberra",
        )

        # Compute the distances between the user and the cached categorical features.
        cat_features = np.array(
            [
                [distance.hamming(x, client_categorical_feats)]
                for x in self.categorical_features
            ]
        )

        # See the "Note about cdist optimization" in README.md for why we only use cdist once.

        # Take the product of similarities to attain a univariate similarity score.
        # Note that the addition of 0.001 to the continuous features
        # sets a floor value to the distance in continuous similarity
        # scores.  There is no such floor value set for categorical
        # features so this adjustment prioritizes categorical
        # similarity over continous similarity
        return (cont_features + FLOOR_DISTANCE_ADJUSTMENT) * cat_features

    def get_similar_donors(self, client_data):
        """Computes a set of :float: similarity scores between a client and a set of candidate
        donors for which comparable variables have been measured.

        A custom similarity metric is defined in this function that combines the Hamming distance
        for categorical variables with the Canberra distance for continuous variables into a
        univariate similarity metric between the client and a set of candidate donors loaded during
        init.

        :param client_data: a client data payload including a subset fo telemetry fields.
        :return: the sorted approximate likelihood ratio (np.array) corresponding to the
                 internally computed similarity score and a list of indices that link
                 each LR score with the related donor in the |self.donors_pool|.
        """
        # Compute the distance between self and any comparable client.
        distances = self.compute_clients_dist(client_data)

        # Compute the LR based on precomputed distributions that relate the score
        # to a probability of providing good addon recommendations.

        lrs_from_scores = np.array(
            [self.get_lr(distances[i]) for i in range(self.num_donors)]
        )

        # Sort the LR values (descending) and return the sorted values together with
        # the original indices.
        indices = (-lrs_from_scores).argsort()
        return lrs_from_scores[indices], indices

    def _recommend(self, client_data, limit, extra_data={}):
        donor_set_ranking, indices = self.get_similar_donors(client_data)
        donor_log_lrs = np.log(donor_set_ranking)
        # 1.0 corresponds to a log likelihood ratio of 0 meaning that donors are equally
        # likely to be 'good'. A value > 0.0 is sufficient, but we like this to be high.
        if donor_log_lrs[0] < 0.1:
            self.logger.warning(
                "Addons recommended with very low similarity score, perhaps donor set is unrepresentative",
                extra={"maximum_similarity": donor_set_ranking[0]},
            )

        # Retrieve the indices of the highest ranked donors and then append their
        # installed addons.
        index_lrs_iter = zip(indices[donor_log_lrs > 0.0], donor_log_lrs)
        recommendations = []
        for (index, lrs) in index_lrs_iter:
            for term in self.donors_pool[index]["active_addons"]:
                candidate = (term, lrs)
                recommendations.append(candidate)
        # Sort recommendations on key (guid name)
        recommendations = sorted(recommendations, key=lambda x: x[0])
        recommendations_out = []
        # recommendations must be sorted for this to work.
        for guid_key, group in groupby(recommendations, key=lambda x: x[0]):
            recommendations_out.append((guid_key, sum(j for i, j in group)))
        # now re-sort on the basis of LLR.
        recommendations_out = sorted(recommendations_out, key=lambda x: -x[1])

        log_data = (
            client_data["client_id"],
            str([r[0] for r in recommendations_out[:limit]]),
        )
        self.logger.info(
            "similarity_recommender_triggered, "
            "client_id: [%s], guids: [%s]" % log_data
        )
        return recommendations_out

    def recommend(self, client_data, limit, extra_data={}):
        try:
            recommendations_out = self._recommend(
                client_data, limit, extra_data
            )
        except Exception as e:
            recommendations_out = []
            self._donors_pool.force_expiry()
            self._lr_curves.force_expiry()

            self.logger.exception(
                "Similarity recommender crashed for {}".format(
                    client_data.get("client_id", "no-client-id")
                ),
                e,
            )

        return recommendations_out[:limit]
