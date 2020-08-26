# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import threading
import redis
import numpy as np
from srgutil.interfaces import IMozLogging
from taar.settings import (
    REDIS_HOST,
    REDIS_PORT,
    TAARLITE_GUID_COINSTALL_BUCKET,
    TAARLITE_GUID_COINSTALL_KEY,
    TAARLITE_GUID_RANKING_KEY,
    TAARLITE_TTL,
)
import time

from jsoncache.loader import s3_json_loader


ACTIVE_DB = "active_db"
UPDATE_CHECK = "update_id_check"


COINSTALL_PREFIX = "coinstall|"
FILTERED_COINSTALL_PREFIX = "filtered_coinstall|"
RANKING_PREFIX = "ranking|"
MIN_INSTALLS_PREFIX = "min_installs|"


# This is a map is guid->sum of coinstall counts
NORMDATA_COUNT_MAP_PREFIX = "normdata_count_map_prefix|"

# Capture the number of times a GUID shows up per row
# of coinstallation data.
NORMDATA_ROWCOUNT_PREFIX = "normdata_rowcount_prefix|"

NORMDATA_GUID_ROW_NORM_PREFIX = "normdata_guid_row_norm_prefix"


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


class AddonsCoinstallCache:
    """
    This class manages a redis instance to hold onto the taar-lite
    GUID->GUID co-installation data
    """

    def __init__(self, ctx, ttl=TAARLITE_TTL):
        self._ctx = ctx
        self.logger = self._ctx[IMozLogging].get_logger("taar")
        self._ttl = ttl

        self._r0 = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        self._r1 = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1)
        self._r2 = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=2)

        # Set (pid, thread_ident) tuple of the first
        self._ident = f"{os.getpid()}_{threading.get_ident()}"

        if self._db() is None:
            self.safe_load_data()

        self.wait_for_data()

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
        self._r0.set(UPDATE_CHECK, self._ident, nx=True, ex=60 * 10)
        self.logger.info(f"UPDATE_CHECK field is set: {self._ident}")

        # This is a concurrency barrier to make sure only the pinned
        # thread can update redis
        update_ident = self._r0.get(UPDATE_CHECK).decode("utf8")
        if update_ident != self._ident:
            return

        # We're past the thread barrier - load the data and clear the
        # barrier when done
        try:
            self._load_data()
        finally:
            self._r0.delete(UPDATE_CHECK)
            self.logger.info("UPDATE_CHECK field is cleared")

    def _load_data(self):
        active_db = self._r0.get(ACTIVE_DB)
        if active_db is not None:
            active_db = int(active_db)
            if active_db == 1:
                next_active_db = 2
            else:
                next_active_db = 1
        else:
            next_active_db = 1

        self._copy_data(next_active_db)

        # Once all data is loaded, just precompute a normalized
        # version
        self.logger.info("Precomputing normalized data")
        self._precompute_normalization(next_active_db)
        self.logger.info("Completed precomputing normalized data")

        # TODO: should this autoexpire to help indicate that no fresh
        # data has loaded?  Maybe N * update TTL time?
        self._r0.set(ACTIVE_DB, next_active_db)

        self.logger.info(f"Active DB is set to {next_active_db}")

    def _copy_data(self, next_active_db):
        if next_active_db == 1:
            db = self._r1
        else:
            db = self._r2

        # Clear this database before we do anything with it
        db.flushdb()
        self._update_coinstall_data(db)
        self._update_rank_data(db)

    def fetch_ranking_data(self):
        return s3_json_loader(TAARLITE_GUID_COINSTALL_BUCKET, TAARLITE_GUID_RANKING_KEY)

    def _update_rank_data(self, db):

        data = self.fetch_ranking_data()

        items = data.items()
        len_items = len(items)

        for i, (guid, count) in enumerate(items):
            db.set(RANKING_PREFIX + guid, json.dumps(count))

            if i % 1000 == 0:
                self.logger.info(f"Loaded {i+1} of {len_items} GUID ranking into redis")

        min_installs = np.mean(list(data.values())) * 0.05
        db.set(MIN_INSTALLS_PREFIX, min_installs)

    def _precompute_normalization(self, next_active_db):

        if next_active_db == 1:
            db = self._r1
        else:
            db = self._r2

        self.logger.info("Precomputing normalization")

        guid_count_map = {}
        row_count = {}
        guid_row_norm = {}

        key_iter_coinstall = PrefixStripper(
            COINSTALL_PREFIX,
            db.scan_iter(match=COINSTALL_PREFIX + "*"),
            cast_to_str=True,
        )
        for guidkey in key_iter_coinstall:
            coinstalls_raw = db.get(COINSTALL_PREFIX + guidkey)
            if coinstalls_raw is None:
                continue
            coinstalls = json.loads(coinstalls_raw.decode("utf8"))

            tmp = dict(
                [(k, v) for (k, v) in coinstalls.items() if v >= self.min_installs]
            )

            self._db().set(FILTERED_COINSTALL_PREFIX + guidkey, tmp)

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

        self.logger.info("guidmaps computed - saving to redis")
        for guid, guid_count in guid_count_map.items():
            self._db().set(NORMDATA_COUNT_MAP_PREFIX + guid, json.dumps(guid_count))

        for coinstall_guid, coinstall_count in row_count.items():
            self._db().set(
                NORMDATA_COUNT_MAP_PREFIX + coinstall_guid, json.dumps(coinstall_count),
            )

        for coinstall_guid, norm_val in guid_row_norm.items():
            self._db().set(
                NORMDATA_GUID_ROW_NORM_PREFIX + coinstall_guid, json.dumps(norm_val),
            )
        self.logger.info("finished saving guidmaps to redis")

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

    @property
    def min_installs(self):
        """
        Return the floor minimum installed addons that we will
        consider, or 0 if nothing is currently stored in redis
        """
        result = self._db().get(MIN_INSTALLS_PREFIX)
        if result is None:
            return 0
        return int(result.decode("utf8"))

    def fetch_coinstall_data(self):
        return s3_json_loader(
            TAARLITE_GUID_COINSTALL_BUCKET, TAARLITE_GUID_COINSTALL_KEY
        )

    def _update_coinstall_data(self, db):

        data = self.fetch_coinstall_data()

        items = data.items()
        len_items = len(items)
        for i, (guid, coinstall_map) in enumerate(items):
            db.set(COINSTALL_PREFIX + guid, json.dumps(coinstall_map))
            if i % 1000 == 0:
                self.logger.info(
                    f"Loaded {i+1} of {len_items} GUID-GUID coinstall records into redis"
                )

    def get_filtered_coinstall(self, guid, default=None):
        tmp = self._db().get(FILTERED_COINSTALL_PREFIX + guid)
        if tmp:
            return json.loads(tmp.decode("utf8"))
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

    def wait_for_data(self):
        while True:
            if not self.is_active():
                break
            self.logger.info("waiting for data. spinlock active")
            time.sleep(1)
        self.logger.info("finished waiting for data")

    def _db(self):
        """
        This dereferences the ACTIVE_DB pointer to get the current
        active redis instance
        """
        active_db = self._r0.get(ACTIVE_DB)
        if active_db is not None:
            db = int(active_db.decode("utf8"))
            if db == 1:
                return self._r1
            elif db == 2:
                return self._r2
