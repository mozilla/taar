from .hbase_client import HBaseClient


class ProfileFetcher:
    """ Fetch the latest information for a client on HBase.
    """
    def __init__(self):
        self.hbase_client = HBaseClient()

    def get(self, client_id):
        addons_list = self.hbase_client.get_client_addons(client_id)
        addon_ids = [addon['addon_id']
                     for addon in addons_list['active_addons']]
        return {"installed_addons": addon_ids}
