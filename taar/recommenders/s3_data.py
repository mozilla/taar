# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .lazys3 import LazyJSONLoader
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
        self._data = LazyJSONLoader(self._ctx, S3_BUCKET, CURATED_WHITELIST)

    def get_whitelist(self):
        return self._data.get()

    def get_randomized_guid_sample(self, item_count):
        """ Fetch a subset of randomzied GUIDs from the whitelist """
        dataset = self.get_whitelist()
        random.shuffle(dataset)
        samples = dataset[:item_count]
        return [s['GUID'] for s in samples]
