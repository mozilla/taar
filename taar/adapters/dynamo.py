# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import boto3
import json
import logging

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
            return json.loads(response['Item']['json_payload'])
        except Exception:
            # Return None on error.  The caller in ProfileFetcher will
            # handle error logging
            return None

    def put_client_profile(self, json_blob):
        """Store a single data record
        """
        return self._table.put_item(Item=json_blob)

    def delete(self, client_id):
        self._table.delete_item(Key={'client_id': client_id})

    def batch_delete(self, *client_ids):
        with self._table.batch_writer() as batch:
            for client_id in client_ids:
                batch.delete_item(Key={'client_id': client_id})

    def batch_put_clients(self, records):
        """Batch fill the DynamoDB instance with
        """
        with self._table.batch_writer() as batch:
            for rec in records:
                batch.put_item(Item=rec)
