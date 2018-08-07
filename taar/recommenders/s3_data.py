# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .utils import get_s3_json_content
import threading
import random

S3_BUCKET = 'telemetry-parquet'
CURATED_WHITELIST = 'telemetry-ml/addon_recommender/top_200_whitelist.json'


class CuratedWhitelistCache:
    """
    This fetches the curated whitelist from S3.

    A sample of the whitelist below :

        [{'GUID': guid_string,
          'Extension': extension_name,
          'Copy (final)': english_description},
        ]
    """
    def __init__(self, ctx):
        self._ctx = ctx
        self._lock = threading.RLock()
        self._json_data = None

    def get_whitelist(self):
        with self._lock:
            # TODO: replace this with the LazyJSONLoader from TAARlite for
            # better performance and expiring dataset
            if self._json_data is not None:
                return self._json_data
            self._json_data = get_s3_json_content(S3_BUCKET, CURATED_WHITELIST)
            return self._json_data

    def get_randomized_guid_sample(self, item_count):
        """ Fetch a subset of randomzied GUIDs from the whitelist """
        dataset = self.get_whitelist()
        random.shuffle(dataset)
        samples = dataset[:item_count]
        return [s['GUID'] for s in samples]
