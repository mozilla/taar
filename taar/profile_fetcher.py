# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from decouple import config
from srgutil.interfaces import IMozLogging
import boto3
import json
import zlib

from taar.recommenders import TEST_CLIENT_IDS, EMPTY_TEST_CLIENT_IDS


DYNAMO_REGION = config("DYNAMO_REGION", default="us-west-2")
DYNAMO_TABLE_NAME = config("DYNAMO_TABLE_NAME", default="taar_addon_data_20180206")


class ProfileController:
    """
    This class provides basic read/write access into a AWS DynamoDB
    backed datastore.  The profile controller and profile fetcher code
    should eventually be merged as individually they don't "pull their
    weight".
    """

    def __init__(self, ctx, region_name, table_name):
        """
        Configure access to the DynamoDB instance
        """
        self._ctx = ctx
        self.logger = self._ctx.get(IMozLogging).get_logger("taar")
        self._ddb = boto3.resource("dynamodb", region_name=region_name)
        self._table = self._ddb.Table(table_name)

    def get_client_profile(self, client_id):
        """This fetches a single client record out of DynamoDB
        """
        try:
            response = self._table.get_item(Key={"client_id": client_id})
            compressed_bytes = response["Item"]["json_payload"].value
            json_byte_data = zlib.decompress(compressed_bytes)
            json_str_data = json_byte_data.decode("utf8")
            return json.loads(json_str_data)
        except KeyError:
            # No client ID found - not really an error
            return None
        except Exception as e:
            # Return None on error.  The caller in ProfileFetcher will
            # handle error logging
            msg = "Error loading client data for {}.  Error: {}"
            self.logger.debug(msg.format(client_id, str(e)))
            return None


class ProfileFetcher:
    """ Fetch the latest information for a client on the backing
    datastore
    """

    def __init__(self, ctx):
        self._ctx = ctx
        self.logger = self._ctx.get(IMozLogging).get_logger("taar")
        self._client = ProfileController(
            self._ctx, region_name=DYNAMO_REGION, table_name=DYNAMO_TABLE_NAME
        )

    def set_client(self, client):
        self._client = client

    def get(self, client_id):

        if client_id in TEST_CLIENT_IDS or client_id in EMPTY_TEST_CLIENT_IDS:
            return {
                "client_id": client_id,
                "geo_city": "Toronto",
                "subsession_length": 42,
                "locale": "en-CA",
                "os": "Linux",
                "installed_addons": [],
                "disabled_addons_ids": [],
                "bookmark_count": 0,
                "tab_open_count": 0,
                "total_uri": 0,
                "unique_tlds": 0,
            }

        profile_data = self._client.get_client_profile(client_id)

        if profile_data is None:
            self.logger.debug(
                "Client profile not found", extra={"client_id": client_id}
            )
            return None

        addon_ids = [
            addon["addon_id"]
            for addon in profile_data.get("active_addons", [])
            if not addon.get("is_system", False)
        ]

        return {
            "client_id": client_id,
            "geo_city": profile_data.get("city", ""),
            "subsession_length": profile_data.get("subsession_length", 0),
            "locale": profile_data.get("locale", ""),
            "os": profile_data.get("os", ""),
            "installed_addons": addon_ids,
            "disabled_addons_ids": profile_data.get("disabled_addons_ids", []),
            "bookmark_count": profile_data.get("places_bookmarks_count", 0),
            "tab_open_count": profile_data.get(
                "scalar_parent_browser_engagement_tab_open_event_count", 0
            ),
            "total_uri": profile_data.get(
                "scalar_parent_browser_engagement_total_uri_count", 0
            ),
            "unique_tlds": profile_data.get(
                "scalar_parent_browser_engagement_unique_domains_count", 0
            ),
        }
