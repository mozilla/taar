# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import threading
import redis

from taar.recommenders.cache import TAARCache, RANKING_PREFIX, COINSTALL_PREFIX
from taar.settings import (
    REDIS_HOST,
    REDIS_PORT,
    TAARLITE_MUTEX_TTL,
)

# This marks which of the redis databases is currently
# active for read
ACTIVE_DB = "active_db"

# This is a mutex to block multiple writers from redis
UPDATE_CHECK = "update_mutex|"


class PrefixStripper:
    def __init__(self, prefix, iterator, cast_to_str=False):
        self._prefix = prefix
        self._iter = iterator
        self._cast_to_str = cast_to_str

    def __iter__(self):
        return self

    def __next__(self):
        result = self._iter.__next__()
        result = result[len(self._prefix):]
        if self._cast_to_str:
            result = str(result)
        return result


class TAARCacheRedis(TAARCache):
    """
    This class manages a redis instance to hold onto the taar-lite
    GUID->GUID co-installation data
    """

    _instance = None

    @classmethod
    def get_instance(cls, ctx):
        if cls._instance is None:
            cls._instance = TAARCacheRedis(ctx, i_didnt_read_the_docs=False)
        return cls._instance

    def __init__(self, ctx, i_didnt_read_the_docs=True):
        super(TAARCacheRedis, self).__init__(ctx, i_didnt_read_the_docs)

        self._last_db = None
        # Keep an integer handle (or None) on the last known database
        self._last_db = None

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

    def _db_get(self, key, default=None, db=None):
        tmp = (db or self._db()).get(key)
        if tmp:
            return json.loads(tmp.decode("utf8"))
        return default

    def _db_set(self, key, val, db):
        db.set(key, json.dumps(val))

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

    def ensure_db_loaded(self):
        _ = self._db()  # make sure we've computed data from the live redis instance

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

        self._build_cache_context(db)
        self.logger.info("Completed precomputing normalized data")

    @property
    def _ident(self):
        """ pid/thread identity """
        return f"{os.getpid()}_{threading.get_ident()}"

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

        if next_active_db == 1:
            db = self._r1
        else:
            db = self._r2

        # Clear this database before we do anything with it
        db.flushdb()

        self._copy_data(db)

        self._r0.set(ACTIVE_DB, next_active_db)
        self.logger.info(f"Active DB is set to {next_active_db}")
