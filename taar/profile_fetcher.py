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

        addon_ids = [addon['addon_id'] for addon in profile_data['active_addons']
                     if not addon.get('is_system', False)]
        return {
            "geo_city": profile_data.get("city"),
            "subsession_length": profile_data.get("subsession_length"),
            "locale": profile_data.get('locale'),
            "os": profile_data.get("os"),
            "installed_addons": addon_ids,
            "disabled_addons_ids": profile_data.get("disabled_addons_ids", []),
            "bookmark_count": profile_data.get("places_bookmarks_count", 0),
            "tab_open_count": profile_data.get("scalar_parent_browser_engagement_tab_open_event_count", 0),
            "total_uri": profile_data.get("scalar_parent_browser_engagement_total_uri_count", 0),
            "unique_tlds": profile_data.get("scalar_parent_browser_engagement_unique_domains_count", 0),
        }
