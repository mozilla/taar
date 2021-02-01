# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import threading
import redis
import numpy as np
from taar.logs import IMozLogging

from taar.settings import (
    REDIS_HOST,
    REDIS_PORT,
)


# TAARLite configuration
from taar.settings import (
    TAARLITE_GUID_COINSTALL_BUCKET,
    TAARLITE_GUID_COINSTALL_KEY,
    TAARLITE_GUID_RANKING_KEY,
    TAARLITE_TRUNCATE,
    TAARLITE_MUTEX_TTL,
)

# TAAR configuration
from taar.settings import (
    # Locale
    TAAR_LOCALE_BUCKET,
    TAAR_LOCALE_KEY,
    # Collaborative dta
    TAAR_ADDON_MAPPING_BUCKET,
    TAAR_ADDON_MAPPING_KEY,
    TAAR_ITEM_MATRIX_BUCKET,
    TAAR_ITEM_MATRIX_KEY,
    # Similarity data
    TAAR_SIMILARITY_BUCKET,
    TAAR_SIMILARITY_DONOR_KEY,
    TAAR_SIMILARITY_LRCURVES_KEY,
    # Ensemble data
    TAAR_ENSEMBLE_BUCKET,
    TAAR_ENSEMBLE_KEY,
    # Whitelist data
    TAAR_WHITELIST_BUCKET,
    TAAR_WHITELIST_KEY,
)

from jsoncache.loader import gcs_json_loader


# This marks which of the redis databases is currently
# active for read
ACTIVE_DB = "active_db"

# This is a mutex to block multiple writers from redis
UPDATE_CHECK = "update_mutex|"


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


class PrefixStripper:
    def __init__(self, prefix, iterator, cast_to_str=False):
        self._prefix = prefix
        self._iter = iterator
        self._cast_to_str = cast_to_str

    def __iter__(self):
        return self

    def __next__(self):
        result = self._iter.__next__()
        result = result[len(self._prefix) :]
        if self._cast_to_str:
            result = str(result)
        return result


class TAARCache:
    """
    This class manages a redis instance to hold onto the taar-lite
    GUID->GUID co-installation data
    """

    _instance = None

    @classmethod
    def get_instance(cls, ctx):
        if cls._instance is None:
            cls._instance = TAARCache(ctx, i_didnt_read_the_docs=False)
        return cls._instance

    def __init__(self, ctx, i_didnt_read_the_docs=True):
        """
        Don't call this directly - use get_instance instace
        """
        if i_didnt_read_the_docs:
            raise RuntimeError(
                "You cannot call this method directly - use get_instance"
            )

        self._ctx = ctx
        self._last_db = None
        self.logger = self._ctx[IMozLogging].get_logger("taar")

        # Keep an integer handle (or None) on the last known database
        self._last_db = None

        self._similarity_num_donors = 0
        self._similarity_continuous_features = None
        self._similarity_categorical_features = None

        rcon = self.init_redis_connections()

        self._r0 = rcon[0]
        self._r1 = rcon[1]
        self._r2 = rcon[2]

    def reset(self):
        # Clear out the r0 bookkeeping to reset the database
        return self._r0.flushdb()

    def info(self):
        """
        Dump bookkeeping metadata to logs
        """
        meta = {}
        for key in self._r0.scan_iter():
            meta[key.decode("utf8")] = self._r0.get(key).decode("utf8")
        if len(meta) == 0:
            self.logger.info("Bookkeeping data for TAARLite cache was empty")
        else:
            self.logger.info("TAARLite cache info", extra=meta)

    def init_redis_connections(self):
        """
        Bind connections to redis databases.  This sits in its own
        method to enable mocking for tests
        """
        return {
            0: redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0),
            1: redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1),
            2: redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2),
        }

    def safe_load_data(self):
        """
        This is a multiprocess, multithread safe method to safely load
        data into the cache.

        If a concurrent calls to this method are invoked, only the first
        call will have any effect.
        """
        # Pin the first thread ID to try to update data
        # Note that nx flag so that this is only set if the
        # UPDATE_CHECK is not previously set
        #
        # The thread barrier will autoexpire in 10 minutes in the
        # event of process termination inside the critical section.
        self._r0.set(UPDATE_CHECK, self._ident, nx=True, ex=TAARLITE_MUTEX_TTL)
        self.logger.info(f"UPDATE_CHECK field is set: {self._ident}")

        # This is a concurrency barrier to make sure only the pinned
        # thread can update redis
        update_ident = self._r0.get(UPDATE_CHECK).decode("utf8")
        if update_ident != self._ident:
            self.logger.info(
                "Cache update lock has already been acquired by another process"
            )
            return

        # We're past the thread barrier - load the data and clear the
        # barrier when done
        try:
            self._load_data()
        finally:
            self._r0.delete(UPDATE_CHECK)
            self.logger.info("UPDATE_CHECK field is cleared")

    def guid_maps_count_map(self, guid, default=None):
        tmp = self._db().get(NORMDATA_COUNT_MAP_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def guid_maps_rowcount(self, guid, default=None):
        tmp = self._db().get(NORMDATA_ROWCOUNT_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def guid_maps_row_norm(self, guid, default=None):
        tmp = self._db().get(NORMDATA_GUID_ROW_NORM_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def min_installs(self, db):
        """
        Return the floor minimum installed addons that we will
        consider, or 0 if nothing is currently stored in redis
        """
        result = db.get(MIN_INSTALLS_PREFIX)
        if result is None:
            return 0
        return float(result.decode("utf8"))

    def get_filtered_coinstall(self, guid, default=None):
        tmp = self._db().get(FILTERED_COINSTALL_PREFIX + guid)
        if tmp:
            raw_dict = json.loads(tmp.decode("utf8"))
            # This truncates the size of the coinstall list for
            # performance reasons
            return dict(
                sorted(raw_dict.items(), key=lambda x: x[1], reverse=True)[
                    :TAARLITE_TRUNCATE
                ]
            )
        return default

    def get_rankings(self, guid, default=None):
        """
        Return the rankings
        """
        tmp = self._db().get(RANKING_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def has_coinstalls_for(self, guid):
        return self._db().get(COINSTALL_PREFIX + guid) is not None

    def get_coinstalls(self, guid, default=None):
        """
        Return a map of GUID:install count that represents the
        coinstallation map for a particular addon GUID
        """
        tmp = self._db().get(COINSTALL_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def key_iter_ranking(self):
        return PrefixStripper(
            RANKING_PREFIX, self._db().scan_iter(match=RANKING_PREFIX + "*")
        )

    def key_iter_coinstall(self):
        return PrefixStripper(
            COINSTALL_PREFIX, self._db().scan_iter(match=COINSTALL_PREFIX + "*")
        )

    def is_active(self):
        """
        return True if data is loaded
        """
        # Any value in ACTIVE_DB indicates that data is live
        return self._r0.get(ACTIVE_DB) is not None

    def top_addons_per_locale(self):
        """
        Get locale data
        """
        tmp = self._db().get(LOCALE_DATA)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return None

    def collab_raw_item_matrix(self):
        """
        Get the taar collaborative item matrix
        """
        tmp = self._db().get(COLLAB_ITEM_MATRIX)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return None

    def collab_addon_mapping(self):
        """
        Get the taar collaborative addon mappin
        """
        tmp = self._db().get(COLLAB_MAPPING_DATA)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return None

    def similarity_donors(self):
        """
        Get the taar similarity donors
        """
        tmp = self._db().get(SIMILARITY_DONORS)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return None

    def similarity_lrcurves(self):
        """
        Get the taar similarity donors
        """
        tmp = self._db().get(SIMILARITY_LRCURVES)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return None

    def similarity_continuous_features(self):
        """
        precomputed similarity recommender continuous features cache
        """
        _ = self._db()  # make sure we've computed data from the live redis instance
        return self._similarity_continuous_features

    def similarity_categorical_features(self):
        """
        precomputed similarity recommender categorical features cache
        """
        _ = self._db()  # make sure we've computed data from the live redis instance
        return self._similarity_categorical_features

    @property
    def similarity_num_donors(self):
        """
        precomputed similarity recommender categorical features cache
        """
        _ = self._db()  # make sure we've computed data from the live redis instance
        return self._similarity_num_donors

    def ensemble_weights(self):
        tmp = self._db().get(ENSEMBLE_WEIGHTS)
        if tmp:
            return json.loads(tmp)
        return None

    def whitelist_data(self):
        tmp = self._db().get(WHITELIST_DATA)
        if tmp:
            return json.loads(tmp)
        return None

    def cache_context(self):
        self._db()
        return self._cache_context

    def _build_cache_context(self):
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
        return tmp

    """

    ################################

    Private methods below

    """

    def _db(self):
        """
        This dereferences the ACTIVE_DB pointer to get the current
        active redis instance
        """
        active_db = self._r0.get(ACTIVE_DB)

        if active_db is not None:
            db = int(active_db.decode("utf8"))

            if db == 1:
                # Run all callback functions to preprocess model data
                live_db = self._r1
            elif db == 2:
                live_db = self._r2

            self._update_data_callback(db, live_db)
            return live_db

    def _update_data_callback(self, db_num, db):
        """
        Preprocess data when the current redis instance does not match
        the last known instance.
        """
        if db_num == self._last_db:
            return

        self._last_db = db_num
        self._build_similarity_features_caches(db)

        self._cache_context = self._build_cache_context()
        self.logger.info("Completed precomputing normalized data")

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

        tmp = db.get(SIMILARITY_DONORS)
        if tmp is None:
            return
        donors_pool = json.loads(tmp.decode("utf8"))

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

    @property
    def _ident(self):
        """ pid/thread identity """
        return f"{os.getpid()}_{threading.get_ident()}"

    def _fetch_coinstall_data(self):
        return gcs_json_loader(
            TAARLITE_GUID_COINSTALL_BUCKET, TAARLITE_GUID_COINSTALL_KEY
        )

    def _fetch_ranking_data(self):
        return gcs_json_loader(TAARLITE_GUID_COINSTALL_BUCKET, TAARLITE_GUID_RANKING_KEY)

    def _fetch_locale_data(self):
        return gcs_json_loader(TAAR_LOCALE_BUCKET, TAAR_LOCALE_KEY)

    def _fetch_collaborative_mapping_data(self):
        return gcs_json_loader(TAAR_ADDON_MAPPING_BUCKET, TAAR_ADDON_MAPPING_KEY)

    def _fetch_collaborative_item_matrix(self):
        return gcs_json_loader(TAAR_ITEM_MATRIX_BUCKET, TAAR_ITEM_MATRIX_KEY)

    def _fetch_similarity_donors(self):
        return gcs_json_loader(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY,)

    def _fetch_similarity_lrcurves(self):
        return gcs_json_loader(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_LRCURVES_KEY,)

    def _fetch_ensemble_weights(self):
        return gcs_json_loader(TAAR_ENSEMBLE_BUCKET, TAAR_ENSEMBLE_KEY)

    def _fetch_whitelist(self):
        return gcs_json_loader(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY)

    def _update_whitelist_data(self, db):
        """
        Load the TAAR whitelist data
        """
        tmp = self._fetch_whitelist()
        if tmp:
            db.set(WHITELIST_DATA, json.dumps(tmp))

    def _update_ensemble_data(self, db):
        """
        Load the TAAR ensemble data
        """
        tmp = self._fetch_ensemble_weights()
        if tmp:
            db.set(ENSEMBLE_WEIGHTS, json.dumps(tmp["ensemble_weights"]))

    def _update_similarity_data(self, db):
        """
        Load the TAAR similarity data
        """
        donors = self._fetch_similarity_donors()
        lrcurves = self._fetch_similarity_lrcurves()

        db.set(SIMILARITY_DONORS, json.dumps(donors))
        db.set(SIMILARITY_LRCURVES, json.dumps(lrcurves))

    def _update_collab_data(self, db):
        """
        Load the TAAR collaborative data.  This is two parts: an item
        matrix and a mapping of GUIDs
        """
        # Load the item matrix into redis
        item_matrix = self._fetch_collaborative_item_matrix()
        db.set(COLLAB_ITEM_MATRIX, json.dumps(item_matrix))

        # Load the taar collaborative mapping data
        mapping_data = self._fetch_collaborative_mapping_data()
        db.set(COLLAB_MAPPING_DATA, json.dumps(mapping_data))

    def _update_locale_data(self, db):
        """
        Load the TAAR locale data
        """
        data = self._fetch_locale_data()
        result = {}
        for locale, guid_list in data.items():
            result[locale] = sorted(guid_list, key=lambda x: x[1], reverse=True)

        db.set(LOCALE_DATA, json.dumps(result))

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

            db.set(FILTERED_COINSTALL_PREFIX + guid, json.dumps(tmp))
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

            db.set(COINSTALL_PREFIX + guid, json.dumps(coinstalls))
            if i % 1000 == 0:
                self.logger.info(
                    f"Loaded {i+1} of {len_items} GUID-GUID coinstall records into redis"
                )

        self.logger.info("guidmaps computed - saving to redis")
        for guid, guid_count in guid_count_map.items():
            db.set(NORMDATA_COUNT_MAP_PREFIX + guid, json.dumps(guid_count))

        for coinstall_guid, coinstall_count in row_count.items():
            db.set(
                NORMDATA_ROWCOUNT_PREFIX + coinstall_guid, json.dumps(coinstall_count),
            )

        for coinstall_guid, norm_val in guid_row_norm.items():
            db.set(
                NORMDATA_GUID_ROW_NORM_PREFIX + coinstall_guid, json.dumps(norm_val),
            )
        self.logger.info("finished saving guidmaps to redis")

    def _update_rank_data(self, db):

        data = self._fetch_ranking_data()

        items = data.items()
        len_items = len(items)

        for i, (guid, count) in enumerate(items):
            db.set(RANKING_PREFIX + guid, json.dumps(count))

            if i % 1000 == 0:
                self.logger.info(f"Loaded {i+1} of {len_items} GUID ranking into redis")

        min_installs = np.mean(list(data.values())) * 0.05
        db.set(MIN_INSTALLS_PREFIX, min_installs)
        self.logger.info(f"Updated MIN_INSTALLS: {min_installs}")

    def _load_data(self):
        active_db = self._r0.get(ACTIVE_DB)
        if active_db is not None:
            active_db = int(active_db.decode("utf8"))
            if active_db == 1:
                next_active_db = 2
            else:
                next_active_db = 1
        else:
            next_active_db = 1

        self._copy_data(next_active_db)

        self._r0.set(ACTIVE_DB, next_active_db)
        self.logger.info(f"Active DB is set to {next_active_db}")

    def _copy_data(self, next_active_db):
        if next_active_db == 1:
            db = self._r1
        else:
            db = self._r2

        # Clear this database before we do anything with it
        db.flushdb()

        # Update TAARlite
        self._update_rank_data(db)
        self._update_coinstall_data(db)

        # Update TAAR locale data
        self._update_locale_data(db)

        # Update TAAR collaborative data
        self._update_collab_data(db)

        # Update TAAR similarity data
        self._update_similarity_data(db)

        # Update TAAR ensemble data
        self._update_ensemble_data(db)

        # Update TAAR ensemble data
        self._update_whitelist_data(db)
