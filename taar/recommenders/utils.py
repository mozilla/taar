import json
import os
from tempfile import gettempdir

import boto3
from botocore.exceptions import ClientError
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


def get_s3_json_content(s3_bucket, s3_key):
    """Download and parse a json file stored on AWS S3.

    The file is downloaded and then cached for future use.
    """
    s3 = boto3.client('s3')
    local_filename = '_'.join([s3_bucket, s3_key]).replace('/', '_')
    local_path = os.path.join(gettempdir(), local_filename)

    if not os.path.exists(local_path):
        with open(local_path, 'wb') as data:
            try:
                s3.download_fileobj(s3_bucket, s3_key, data)
            except ClientError:
                return None
        with open(local_path, 'r') as data:
            return json.loads(data.read())
