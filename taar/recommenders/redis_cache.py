# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import threading
import redis
from srgutil.interfaces import IMozLogging
from taar.settings import (
    REDIS_HOST,
    REDIS_PORT,
    TAARLITE_GUID_COINSTALL_BUCKET,
    TAARLITE_GUID_COINSTALL_KEY,
    TAARLITE_TTL,
)
import time

from jsoncache.loader import s3_json_loader


ACTIVE_DB = "active_db"
UPDATE_CHECK = "update_id_check"


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
        if self.db() is None:
            self.load_data()

        self.wait_for_data()

    def load_data(self):
        # Pin the first thread ID to try to update data
        # Note that nx flag so that this is only set if the
        # UPDATE_CHECK is not previously set
        self._r0.set(UPDATE_CHECK, self._ident, nx=True)
        self.logger.info(f"UPDATE_CHECK field is set: {self._ident}")

        update_ident = self._r0.get(UPDATE_CHECK).decode("utf8")
        if update_ident != self._ident:
            # this is a thread barrier to make sure only the pinned
            # thread can update redis
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
        self._r0.set(ACTIVE_DB, next_active_db)
        # TODO: spin a thread to delete the old_db database
        self.logger.info(f"Active DB is set to {next_active_db}")

    def _copy_data(self, next_active_db):
        data = s3_json_loader(
            TAARLITE_GUID_COINSTALL_BUCKET, TAARLITE_GUID_COINSTALL_KEY
        )
        if next_active_db == 1:
            db = self._r1
        else:
            db = self._r2

        items = data.items()
        len_items = len(items)
        for i, (guid, coinstall_map) in enumerate(items):
            db.set(guid, json.dumps(coinstall_map))
            if i % 1000 == 0:
                self.logger.debug(
                    f"Loaded {i+1} of {len_items} GUID-GUID coinstall records to db:{next_active_db}"
                )

    def wait_for_data(self):
        while True:
            active_db = self._r0.get(ACTIVE_DB)
            if active_db is not None:
                break
            self.logger.debug("waiting for data. spinlock active")
            time.sleep(1)
        self.logger.debug("finished waiting for data")

    def db(self):
        active_db = self._r0.get(ACTIVE_DB)
        if active_db is not None:
            db = int(active_db.decode("utf8"))
            if db == 1:
                return self._r1
            elif db == 2:
                return self._r2
