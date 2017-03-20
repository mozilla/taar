import requests


def fetch_json(uri):
    """ Perform an HTTP GET on the given uri, return the results as json.

    Args:
        uri: the string URI to fetch.

    Returns:
        A JSON object with the response or None if the status code of the
        response is an error code.
    """
    r = requests.get(uri)
    if r.status_code != requests.codes.ok:
        return None

    return r.json()
