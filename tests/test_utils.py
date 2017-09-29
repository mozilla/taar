import boto3
import json
import taar.recommenders.utils as utils
from moto import mock_s3


@mock_s3
def test_get_non_existing():
    bucket = 'test-bucket'
    key = 'non-existing.json'

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)

    assert utils.get_s3_json_content(bucket, key) is None


@mock_s3
def test_get_corrupted():
    bucket = 'test-bucket'
    key = 'corrupted.json'

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)

    # Write a corrupted file to the mocked S3.
    conn.Object(bucket, key).put(Body='This is invalid JSON.')

    assert utils.get_s3_json_content(bucket, key) is None


@mock_s3
def test_get_valid():
    bucket = 'test-bucket'
    key = 'valid.json'

    conn = boto3.resource('s3', region_name='us-west-2')
    conn.create_bucket(Bucket=bucket)

    # Write a corrupted file to the mocked S3.
    sample_data = {"test": "data"}
    conn.Object(bucket, key).put(Body=json.dumps(sample_data))

    assert utils.get_s3_json_content(bucket, key) == sample_data
