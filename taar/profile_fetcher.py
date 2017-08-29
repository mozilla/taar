import logging
from .hbase_client import HBaseClient


logger = logging.getLogger(__name__)


class ProfileFetcher:
    """ Fetch the latest information for a client on HBase.
    """
    def __init__(self, hbase_client=None):
        if hbase_client is None:
            self.hbase_client = HBaseClient()
        else:
            self.hbase_client = hbase_client

    def get(self, client_id):
        profile_data = self.hbase_client.get_client_profile(client_id)

        if profile_data is None:
            logger.error("Client profile not found", extra={"client_id": client_id})
            return None

        addon_ids = [addon['addon_id'] for addon in profile_data['active_addons']]
        return {
            "installed_addons": addon_ids,
            "locale": profile_data['locale']
        }
