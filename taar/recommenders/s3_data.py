# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .utils import get_s3_json_content

S3_BUCKET = 'telemetry-parquet'
CURATED_WHITELIST = 'telemetry-ml/addon_recommender/top_200_whitelist.json'


class WhitelistCache:
    def __init__(self, ctx):
        self._ctx = ctx

        # Enable this check when we start using srgutils
        # assert 'cache' in self._ctx

    def get_curated_whitelist(self):
        # TODO: replace this with the context version so we can inject
        # S3 content easily
        json_data = get_s3_json_content(S3_BUCKET, CURATED_WHITELIST)
        return json_data
