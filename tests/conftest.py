"""
These are global fixtures automagically loaded by pytest
"""

import json
import pytest
import boto3
from srgutil.interfaces import IClock

from taar.context import default_context
from taar.recommenders.s3config import (
    TAAR_WHITELIST_BUCKET,
    TAAR_WHITELIST_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
)

FAKE_LOCALE_DATA = {
    "te-ST": [
        "{1e6b8bce-7dc8-481c-9f19-123e41332b72}",
        "some-other@nice-addon.com",
        "{66d1eed2-a390-47cd-8215-016e9fa9cc55}",
        "{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}",
    ],
    "en": ["some-uuid@test-addon.com", "other-addon@some-id.it"],
}


@pytest.fixture
def test_ctx():
    ctx = default_context()
    ctx.set("clock", ctx.get(IClock))
    return ctx


def install_no_curated_data(ctx):
    conn = boto3.resource(
        "s3",
        region_name="us-west-2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    conn.create_bucket(Bucket=TAAR_WHITELIST_BUCKET)
    conn.Object(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY).put(Body="")

    return ctx


def install_mock_curated_data(ctx):
    mock_data = []
    for i in range(20):
        mock_data.append(str(i) * 16)

    conn = boto3.resource(
        "s3",
        region_name="us-west-2",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    conn.create_bucket(Bucket=TAAR_WHITELIST_BUCKET)
    conn.Object(TAAR_WHITELIST_BUCKET, TAAR_WHITELIST_KEY).put(
        Body=json.dumps(mock_data)
    )

    return ctx
