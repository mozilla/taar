import boto3
import json
import logging
import requests
import requests.exceptions


logger = logging.getLogger(__name__)


def fetch_json(uri):
    """ Perform an HTTP GET on the given uri, return the results as json.

    Args:
        uri: the string URI to fetch.

    Returns:
        A JSON object with the response or None if the status code of the
        response is an error code.
    """
    try:
        r = requests.get(uri)
        if r.status_code != requests.codes.ok:
            return None
        return r.json()
    except requests.exceptions.ConnectionError:
        return None


def get_s3_json_content(s3_bucket, s3_key):
    """Download and parse a json file stored on AWS S3.

    The file is downloaded and then cached for future use.
    """

    raw_data = None
    try:
        s3 = boto3.resource('s3')
        raw_data = (
            s3
            .Object(s3_bucket, s3_key)
            .get()['Body']
            .read()
            .decode('utf-8')
        )
    except Exception:
        logger.exception("Failed to download from S3", extra={
            "bucket": s3_bucket,
            "key": s3_key})
        return None

    # It can happen to have corrupted files. Account for the
    # sad reality of life.
    try:
        return json.loads(raw_data)
    except ValueError:
        logging.error("Cannot parse JSON resource from S3", extra={
            "bucket": s3_bucket,
            "key": s3_key})

    return None
