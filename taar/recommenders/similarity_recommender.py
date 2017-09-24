import logging
from ..recommenders import utils
from .base_recommender import BaseRecommender
from scipy.spatial import distance

CATEGORICAL_FEATURES = ["geo_city", "locale", "os"]
CONTINUOUS_FEATURES = ["subsession_length", "bookmark_count", "tab_open_count", "total_uri", "unique_tlds"]

S3_BUCKET = 'telemetry-parquet'
DONOR_LIST_KEY = 'taar/similarity/donors.json'
LR_CURVES_SIMILARITY_TO_PROBABILITY = 'taar/similarity/lr_curves.json'

logger = logging.getLogger(__name__)


class SimilarityRecommender(BaseRecommender):
    """ A recommender class that returns top N addons based on the client similarity
    with a set of candidate addon donors. Several telemetry fields are used to compute
    pairwise similarity with the donors and similarities are converted into a likelihood
    ratio of being a good match versus not being a good match. These quantities are then
    used to rank specific addons for recommendation.

    This will load a json file containing updated list of addon donors updated periodically
    by a separate weekly process using Longitdudinal Telemetry data.

    This recommender may provide useful recommendations when collaborative_recommender
    may not work.
    """

    def __init__(self):
        self.donors_list = []

        # Download the addon donors list.
        donors_pool = utils.get_s3_json_content(S3_BUCKET, DONOR_LIST_KEY)
        if donors_pool is None:
            logger.error("Cannot download the donor list: {}".format(DONOR_LIST_KEY))

        for donor in donors_pool:
            # Separate out the categorical and numerical features for the donor.
            d = {
                'categorical_features': [donor.get(specified_key) for specified_key in CATEGORICAL_FEATURES],
                'continuous_features': [donor.get(specified_key) for specified_key in CONTINUOUS_FEATURES],
                'active_addons': donor['active_addons']
            }
            self.donors_list.append(d)

        # Download the probability mapping curves from similarity to likelihood of being a good donor.
        self.lr_curves = utils.get_s3_json_content(S3_BUCKET, LR_CURVES_SIMILARITY_TO_PROBABILITY)
        if self.lr_curves is None:
            logger.error("Cannot download the lr curves: {}".format(LR_CURVES_SIMILARITY_TO_PROBABILITY))

    def can_recommend(self, client_data):
        # We can't recommend if we don't have our data files.
        if self.donors_list is None or self.lr_curves is None:
            return False

        # Check that the client info contains a non-None value for each required
        # telemetry field.
        REQUIRED_FIELDS = CATEGORICAL_FEATURES + CONTINUOUS_FEATURES

        has_fields = all([client_data.get(f, None) is not None for f in REQUIRED_FIELDS])
        if not has_fields:
            # Can not add extra info because client_id may not be available.
            logger.error("Unusable client data encountered")
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
        index = [abs(score - s[0]) for s in self.lr_curves]

        # Find the index of the closest value that was precomputed in lr_curves
        _, idx = min((val, idx) for (idx, val) in enumerate(index))

        numer_val = self.lr_curves[idx][1][0]
        denum_val = self.lr_curves[idx][1][1]

        # Compute LR based on numerator and denominator values
        return float(numer_val) / float(denum_val)

    def get_similar_donors(self, client_data):
        """Computes a set of :float: similarity scores between a client and a set of candidate
        donors for which comparable variables have been measured.

        A custom similarity metric is defined in this function that combines the Hamming distance
        for categorical variables with the Canberra distance for continuous variables into a
        univariate similarity metric between the client and a set of candidate donors loaded during
        init.

        :param client_data: a client data payload including a subset fo telemetry fields.
        :rtype: :list:`tuples`: the approximate likelihood ratio corresponding to the
        internally computed similarity score and a list of addons taken from that donor
        """
        client_categorical_feats = [client_data.get(specified_key) for specified_key in CATEGORICAL_FEATURES]
        client_continuous_feats = [client_data.get(specified_key) for specified_key in CONTINUOUS_FEATURES]

        donor_set = []

        # This could be optimized by using cdist, however both logging and debugging benefit from having it in a loop.
        # If performance improvements are necessary in he future, this is a good place to start.
        for donor_index, donor in enumerate(self.donors_list):
            # Compute the similarity score between the donor and the client in the space of categorical features.
            try:
                # Here a larger distance indicates a poorer match between categorical variables.
                j_d = (distance.hamming(client_categorical_feats, donor['categorical_features']))
            except ValueError:
                logger.error("Unable to compute similarity over categorical features.",
                             extra={"client_id": client_data["client_id"]})
            # Compute the similarity score between the donor and the client in the space of numerical features.
            try:
                # Here a value close to zero indicates a good match in continuous variables.
                j_c = (distance.canberra(client_continuous_feats, donor['continuous_features']))
            except ValueError:
                logger.error("Unable to compute similarity over continuous features.",
                             extra={"client_id": client_data["client_id"]})

            # Take the product of similarities to attain a univariate similarity score.
            # Addition of 0.001 to j_c avoids a zero value from the categorical variables, allowing j_d precedence
            single_score = abs((j_c + 0.001) * j_d)

            # compute the LR based on precomputed distributions that relate the score
            #  to a probability of providing good addon recommendations
            lr_from_score = self.get_lr(single_score)
            donor_set.append((lr_from_score, donor_index))
            donor_index += 1

        return sorted(donor_set, reverse=True)

    def recommend(self, client_data, limit=10):
        donor_set_ranking = self.get_similar_donors(client_data)
        # 2.0 corresponds to a likelihood ratio of 2 meaning that donors are less than twice
        # as likely to be 'good'. A value > 1.0 is sufficient, but we like this to be high.
        if donor_set_ranking[0][0] < 2.0:
            logger.warning("Addons recommended with very low similarity score, perhaps donor set is unrepresentative",
                           extra={"maximum_similarity": donor_set_ranking[0]})

        recommendations = []
        for donor_ranking in donor_set_ranking:
            # This expects a list of lists, if singletons are included, they should single elements lists.
            if donor_ranking[0] > 1.0:
                # Retrieve the index of the highest ranked donors and then append their installed addons
                recommendations.extend(self.donors_list[donor_ranking[1]]['active_addons'])
            if len(recommendations) > limit:
                break
        return recommendations[:limit]
