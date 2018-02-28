# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import json
import logging
import zlib

logger = logging.getLogger(__name__)


class ProfileController:
    """
    This class provides basic read/write access into a AWS DynamoDB
    backed datastore.  The profile controller and profile fetcher code
    should eventually be merged as individually they don't "pull their
    weight".
    """

    def __init__(self, region_name, table_name):
        """
        Configure access to the DynamoDB instance
        """
        self._ddb = boto3.resource('dynamodb', region_name=region_name)
        self._table = self._ddb.Table(table_name)

    def get_client_profile(self, client_id):
        """This fetches a single client record out of DynamoDB
        """
        try:
            response = self._table.get_item(Key={'client_id': client_id})
            compressed_bytes = response['Item']['json_payload'].value
            json_byte_data = zlib.decompress(compressed_bytes)
            json_str_data = json_byte_data.decode('utf8')
            return json.loads(json_str_data)
        except Exception:
            # Return None on error.  The caller in ProfileFetcher will
            # handle error logging
            logger.error("Error loading client data for [%s]" % client_id)
            return None
