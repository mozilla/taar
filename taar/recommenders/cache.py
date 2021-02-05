import numpy as np
import bz2
import io
import json
from google.cloud import storage

from taar.interfaces import IMozLogging, ITAARCache

# taarlite guid guid coinstallation matrix
COINSTALL_PREFIX = "coinstall|"

# taarlite guid guid coinstallation matrix filtered by
# minimum installation threshholds
FILTERED_COINSTALL_PREFIX = "filtered_coinstall|"

# taarlite ranking data
RANKING_PREFIX = "ranking|"

# taarlite minimum installation threshold
MIN_INSTALLS_PREFIX = "min_installs|"

# taarlite map of guid->(sum of coinstall counts)
NORMDATA_COUNT_MAP_PREFIX = "normdata_count_map_prefix|"

# taarlite number of times a GUID shows up per row
# of coinstallation data.
NORMDATA_ROWCOUNT_PREFIX = "normdata_rowcount_prefix|"

# taarlite row nownormalization data
NORMDATA_GUID_ROW_NORM_PREFIX = "normdata_guid_row_norm_prefix|"

# TAAR: Locale data
LOCALE_DATA = "taar_locale_data|"

# TAAR: collaborative data
COLLAB_MAPPING_DATA = "taar_collab_mapping|"
COLLAB_ITEM_MATRIX = "taar_collab_item_matrix|"

# TAAR: similarity data
SIMILARITY_DONORS = "taar_similarity_donors|"
SIMILARITY_LRCURVES = "taar_similarity_lrcurves|"

# TAAR: similarity preprocessed data
SIMILARITY_NUM_DONORS = "taar_similarity_num_donors|"
SIMILARITY_CONTINUOUS_FEATURES = "taar_similarity_continuous_features|"
SIMILARITY_CATEGORICAL_FEATURES = "taar_similarity_categorical_features|"

# TAAR: ensemble weights

ENSEMBLE_WEIGHTS = "taar_ensemble_weights|"

# TAAR: whitelist data
WHITELIST_DATA = "taar_whitelist_data|"


class TAARCache(ITAARCache):
    _instance = None

    """
    Design of this class is heavily influenced by TAARCacheRedis needs.
    In fact, it was extracted from TAARCacheRedis  to be used in
        EnsembleRecommender weights update Spark job independently from Redis
    """

    def __init__(self, ctx):
        """
        Don't call this directly - use get_instance instace
        """
        self._dict_db = {}

        self._similarity_num_donors = 0
        self._similarity_continuous_features = None
        self._similarity_categorical_features = None

        self._ctx = ctx
        self._last_db = None

        self.logger = None

        moz_logging = self._ctx.get(IMozLogging)
        self._settings = self._ctx['cache_settings']
        self.logger = moz_logging.get_logger("taar") if moz_logging else None

    @classmethod
    def get_instance(cls, ctx):
        if cls._instance is None:
            cls._instance = TAARCache(ctx)
        return cls._instance

    # TAARCacheRedis compatibility

    def safe_load_data(self):
        if len(self._dict_db) == 0:
            self._copy_data(self._dict_db)
            self._build_cache_context(self._dict_db)

    def _db_get(self, key, default=None, db=None):
        self.safe_load_data()
        return (db or self._dict_db).get(key, default)

    def _db_set(self, key, val, db):
        self._dict_db[key] = val

    def is_active(self):
        """
        return True if data is loaded
        """
        return len(self._dict_db) > 0

    def ensure_db_loaded(self):
        self.safe_load_data()

    def cache_context(self):
        self.ensure_db_loaded()
        return self._cache_context

    # Getters

    def guid_maps_count_map(self, guid, default=None):
        return self._db_get(NORMDATA_COUNT_MAP_PREFIX + guid) or default

    def guid_maps_rowcount(self, guid, default=None):
        return self._db_get(NORMDATA_ROWCOUNT_PREFIX + guid) or default

    def guid_maps_row_norm(self, guid, default=None):
        return self._db_get(NORMDATA_GUID_ROW_NORM_PREFIX + guid) or default

    def min_installs(self, db):
        """
        Return the floor minimum installed addons that we will
        consider, or 0 if nothing is currently stored in redis
        """
        result = self._db_get(MIN_INSTALLS_PREFIX, db=db)
        if result is None:
            return 0
        return float(result)

    def get_filtered_coinstall(self, guid, default=None):
        tmp = self._db_get(FILTERED_COINSTALL_PREFIX + guid)
        if tmp:
            raw_dict = tmp
            # This truncates the size of the coinstall list for
            # performance reasons
            return dict(
                sorted(raw_dict.items(), key=lambda x: x[1], reverse=True)[:self._settings.TAARLITE_TRUNCATE]
            )
        return default

    def get_rankings(self, guid, default=None):
        """
        Return the rankings
        """
        return self._db_get(RANKING_PREFIX + guid) or default

    def has_coinstalls_for(self, guid):
        return self._db_get(COINSTALL_PREFIX + guid) is not None

    def get_coinstalls(self, guid, default=None):
        """
        Return a map of GUID:install count that represents the
        coinstallation map for a particular addon GUID
        """
        return self._db_get(COINSTALL_PREFIX + guid) or default

    def top_addons_per_locale(self):
        """
        Get locale data
        """
        return self._db_get(LOCALE_DATA)

    def collab_raw_item_matrix(self):
        """
        Get the taar collaborative item matrix
        """
        return self._db_get(COLLAB_ITEM_MATRIX)

    def collab_addon_mapping(self):
        """
        Get the taar collaborative addon mappin
        """
        return self._db_get(COLLAB_MAPPING_DATA)

    def similarity_donors(self):
        """
        Get the taar similarity donors
        """
        return self._db_get(SIMILARITY_DONORS)

    def similarity_lrcurves(self):
        """
        Get the taar similarity donors
        """
        return self._db_get(SIMILARITY_LRCURVES)

    def similarity_continuous_features(self):
        """
        precomputed similarity recommender continuous features cache
        """
        self.ensure_db_loaded()
        return self._similarity_continuous_features

    def similarity_categorical_features(self):
        """
        precomputed similarity recommender categorical features cache
        """
        self.ensure_db_loaded()
        return self._similarity_categorical_features

    @property
    def similarity_num_donors(self):
        """
        precomputed similarity recommender categorical features cache
        """
        self.ensure_db_loaded()
        return self._similarity_num_donors

    def ensemble_weights(self):
        return self._db_get(ENSEMBLE_WEIGHTS)

    def whitelist_data(self):
        return self._db_get(WHITELIST_DATA)

    # GCS fetching

    def _load_from_gcs(self, bucket, path):
        """
        Load a JSON object off of a GCS bucket and path.

        If the path ends with '.bz2', decompress the object prior to JSON
        decode.
        """
        try:
            with io.BytesIO() as tmpfile:
                client = storage.Client()
                bucket = client.get_bucket(bucket)
                blob = bucket.blob(path)
                blob.download_to_file(tmpfile)
                tmpfile.seek(0)
                payload = tmpfile.read()

                if path.endswith(".bz2"):
                    payload = bz2.decompress(payload)
                    path = path[:-4]

                if path.endswith(".json"):
                    payload = json.loads(payload.decode("utf8"))

                return payload
        except Exception:
            self.logger.exception(f"Error loading from gcs://{bucket}/{path}")

        return None

    def _fetch_coinstall_data(self):
        return self._load_from_gcs(self._settings.TAARLITE_GUID_COINSTALL_BUCKET,
                                   self._settings.TAARLITE_GUID_COINSTALL_KEY)

    def _fetch_ranking_data(self):
        return self._load_from_gcs(self._settings.TAARLITE_GUID_COINSTALL_BUCKET,
                                   self._settings.TAARLITE_GUID_RANKING_KEY)

    def _fetch_locale_data(self):
        return self._load_from_gcs(self._settings.TAAR_LOCALE_BUCKET, self._settings.TAAR_LOCALE_KEY)

    def _fetch_collaborative_mapping_data(self):
        return self._load_from_gcs(self._settings.TAAR_ADDON_MAPPING_BUCKET, self._settings.TAAR_ADDON_MAPPING_KEY)

    def _fetch_collaborative_item_matrix(self):
        return self._load_from_gcs(self._settings.TAAR_ITEM_MATRIX_BUCKET, self._settings.TAAR_ITEM_MATRIX_KEY)

    def _fetch_similarity_donors(self):
        return self._load_from_gcs(self._settings.TAAR_SIMILARITY_BUCKET, self._settings.TAAR_SIMILARITY_DONOR_KEY)

    def _fetch_similarity_lrcurves(self):
        return self._load_from_gcs(self._settings.TAAR_SIMILARITY_BUCKET, self._settings.TAAR_SIMILARITY_LRCURVES_KEY)

    def _fetch_ensemble_weights(self):
        return self._load_from_gcs(self._settings.TAAR_ENSEMBLE_BUCKET, self._settings.TAAR_ENSEMBLE_KEY)

    def _fetch_whitelist(self):
        return self._load_from_gcs(self._settings.TAAR_WHITELIST_BUCKET, self._settings.TAAR_WHITELIST_KEY)

    # Data update

    def _build_cache_context(self, db):

        self._build_similarity_features_caches(db)

        """
        Fetch from redis once per request
        """
        tmp = {
            # Similarity stuff
            "lr_curves": self.similarity_lrcurves(),
            "num_donors": self.similarity_num_donors,
            "continuous_features": self.similarity_continuous_features(),
            "categorical_features": self.similarity_categorical_features(),
            "donors_pool": self.similarity_donors(),
            # Collaborative
            "addon_mapping": self.collab_addon_mapping(),
            "raw_item_matrix": self.collab_raw_item_matrix(),
            # Locale
            "top_addons_per_locale": self.top_addons_per_locale(),
            # Ensemble
            "whitelist": self.whitelist_data(),
            "ensemble_weights": self.ensemble_weights(),
        }

        def compute_collab_model(val):
            if val not in (None, ""):
                num_rows = len(val)
                num_cols = len(val[0]["features"])

                model = np.zeros(shape=(num_rows, num_cols))
                for index, row in enumerate(val):
                    model[index, :] = row["features"]
            else:
                model = None
            return model

        tmp["collab_model"] = compute_collab_model(tmp["raw_item_matrix"])
        self._cache_context = tmp

    def _build_similarity_features_caches(self, db):
        """
        This function build two feature cache matrices and sets the
        number of donors (self.similarity_num_donors)

        That's the self.categorical_features and
        self.continuous_features attributes.

        One matrix is for the continuous features and the other is for
        the categorical features. This is needed to speed up the similarity
        recommendation process."""
        from taar.recommenders.similarity_recommender import (
            CONTINUOUS_FEATURES,
            CATEGORICAL_FEATURES,
        )

        donors_pool = self._db_get(SIMILARITY_DONORS, db=db)
        if donors_pool is None:
            return

        self._similarity_num_donors = len(donors_pool)

        # Build a numpy matrix cache for the continuous features.
        continuous_features = np.zeros(
            (self.similarity_num_donors, len(CONTINUOUS_FEATURES))
        )

        for idx, d in enumerate(donors_pool):
            features = [d.get(specified_key) for specified_key in CONTINUOUS_FEATURES]
            continuous_features[idx] = features
        self._similarity_continuous_features = continuous_features

        # Build the cache for categorical features.
        categorical_features = np.zeros(
            (self.similarity_num_donors, len(CATEGORICAL_FEATURES)), dtype="object",
        )
        for idx, d in enumerate(donors_pool):
            features = [d.get(specified_key) for specified_key in CATEGORICAL_FEATURES]
            categorical_features[idx] = np.array([features], dtype="object")

        self._similarity_categorical_features = categorical_features

        self.logger.info("Reconstructed matrices for similarity recommender")

    def _update_whitelist_data(self, db):
        """
        Load the TAAR whitelist data
        """
        tmp = self._fetch_whitelist()
        if tmp:
            self._db_set(WHITELIST_DATA, tmp, db)

    def _update_ensemble_data(self, db):
        """
        Load the TAAR ensemble data
        """
        tmp = self._fetch_ensemble_weights()
        if tmp:
            self._db_set(ENSEMBLE_WEIGHTS, tmp["ensemble_weights"], db)

    def _update_similarity_data(self, db):
        """
        Load the TAAR similarity data
        """
        donors = self._fetch_similarity_donors()
        lrcurves = self._fetch_similarity_lrcurves()

        self._db_set(SIMILARITY_DONORS, donors, db)
        self._db_set(SIMILARITY_LRCURVES, lrcurves, db)

    def _update_collab_data(self, db):
        """
        Load the TAAR collaborative data.  This is two parts: an item
        matrix and a mapping of GUIDs
        """
        # Load the item matrix into redis
        item_matrix = self._fetch_collaborative_item_matrix()
        self._db_set(COLLAB_ITEM_MATRIX, item_matrix, db)

        # Load the taar collaborative mapping data
        mapping_data = self._fetch_collaborative_mapping_data()
        self._db_set(COLLAB_MAPPING_DATA, mapping_data, db)

    def _update_locale_data(self, db):
        """
        Load the TAAR locale data
        """
        data = self._fetch_locale_data()
        result = {}
        for locale, guid_list in data.items():
            result[locale] = sorted(guid_list, key=lambda x: x[1], reverse=True)

        self._db_set(LOCALE_DATA, result, db)

    def _update_coinstall_data(self, db):
        """
        Load the TAAR Lite GUID GUID coinstallation data
        """

        data = self._fetch_coinstall_data()

        items = data.items()
        len_items = len(items)

        guid_count_map = {}
        row_count = {}
        guid_row_norm = {}

        for i, (guid, coinstalls) in enumerate(items):

            tmp = dict(
                [(k, v) for (k, v) in coinstalls.items() if v >= self.min_installs(db)]
            )

            self._db_set(FILTERED_COINSTALL_PREFIX + guid, tmp, db)
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

            self._db_set(COINSTALL_PREFIX + guid, coinstalls, db)
            if i % 1000 == 0:
                self.logger.info(
                    f"Loaded {i + 1} of {len_items} GUID-GUID coinstall records into redis"
                )

        self.logger.info("guidmaps computed - saving")

        for guid, guid_count in guid_count_map.items():
            self._db_set(NORMDATA_COUNT_MAP_PREFIX + guid, guid_count, db)

        for coinstall_guid, coinstall_count in row_count.items():
            self._db_set(NORMDATA_ROWCOUNT_PREFIX + coinstall_guid, coinstall_count, db)

        for coinstall_guid, norm_val in guid_row_norm.items():
            self._db_set(NORMDATA_GUID_ROW_NORM_PREFIX + coinstall_guid, norm_val, db)

        self.logger.info("finished saving guidmaps")

    def _update_rank_data(self, db):

        data = self._fetch_ranking_data()

        items = data.items()
        len_items = len(items)

        for i, (guid, count) in enumerate(items):
            self._db_set(RANKING_PREFIX + guid, count, db)

            if i % 1000 == 0:
                self.logger.info(f"Loaded {i + 1} of {len_items} GUID ranking into redis")

        min_installs = np.mean(list(data.values())) * 0.05
        self._db_set(MIN_INSTALLS_PREFIX, min_installs, db)

        self.logger.info(f"Updated MIN_INSTALLS: {min_installs}")

    def _copy_data(self, db):

        # Update TAARlite
        # it loads a lot of data which we don't need for Ensemble Spark job
        if not self._settings.DISABLE_TAAR_LITE:
            self._update_rank_data(db)
            self._update_coinstall_data(db)

        # Update TAAR locale data
        self._update_locale_data(db)

        # Update TAAR collaborative data
        self._update_collab_data(db)

        # Update TAAR similarity data
        self._update_similarity_data(db)

        if not self._settings.DISABLE_ENSEMBLE:
            # Update TAAR ensemble data
            self._update_ensemble_data(db)

            # Update TAAR ensemble data
            self._update_whitelist_data(db)
