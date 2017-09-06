import boto3
import os
import taar.recommenders.utils as utils
from moto import mock_s3


@mock_s3
def test_get_non_existing():
    bucket = 'test-bucket'
    key = 'non-existing.json'

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)

    assert utils.get_s3_json_content(bucket, key) is None
    assert os.path.exists(utils.get_s3_cache_filename(bucket, key)) is False


@mock_s3
def test_get_corrupted():
    bucket = 'test-bucket'
    key = 'corrupted.json'

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)

    # Write a corrupted file to the mocked S3.
    conn.Object(bucket, key).put(Body='This is invalid JSON.')

    assert utils.get_s3_json_content(bucket, key) is None
    assert os.path.exists(utils.get_s3_cache_filename(bucket, key)) is False
