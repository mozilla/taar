# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import time
import threading


class Clock:
    def time(self):
        """Return epoch time in seconds like time.time()"""
        return time.time()


class JSONCache:
    """
    This class keeps a cache of JSON blobs and S3 bucket data.

    All data is expired simultaneously
    """
    def __init__(self, ctx):
        assert 'utils' in ctx
        assert 'clock' in ctx
        self._ctx = ctx

        # Set to 4 hours
        self._ttl = 60 * 60 * 4

        self._json_cache = {}
        self._s3_json_cache = {}

        self.refresh_expiry()

        self._lock = threading.RLock()

    def refresh_expiry(self):
        self._expiry_time = self._ctx['clock'].time() + self._ttl

    def fetch_json(self, url):
        with self._lock:
            utils = self._ctx['utils']
            if url not in self._json_cache:
                self._json_cache[url] = utils.fetch_json(url)
            content = self._json_cache[url]
            self.expire_cache()
            return content

    def get_s3_json_content(self, s3_bucket, s3_key):
        with self._lock:
            utils = self._ctx['utils']
            key = (s3_bucket, s3_key)
            if key not in self._s3_json_cache:
                self._s3_json_cache[key] = utils.get_s3_json_content(s3_bucket, s3_key)
            content = self._s3_json_cache[key]
            self.expire_cache()
            return content

    def expire_cache(self):
        with self._lock:
            clock = self._ctx['clock']

            if clock.time() >= self._expiry_time:
                self._json_cache.clear()
                self._s3_json_cache.clear()
                self.refresh_expiry()
