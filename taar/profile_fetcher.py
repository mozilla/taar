# import requests


class ProfileFetcher:
    """ Fetch the latest information for a client on HBase.
    """
    def __init__(self):
        pass

    def get(self, client_id):
        # TODO
        client_info = {
            "installed_addons": [
                "uBlock0@raymondhill.net",
            ],
        }

        return client_info
