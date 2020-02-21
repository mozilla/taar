# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from taar.recommenders.lazys3 import LazyJSONLoader

import boto3
import pickle
from moto import mock_s3


from taar.recommenders.s3config import (
    TAAR_SIMILARITY_BUCKET,
    TAAR_SIMILARITY_DONOR_KEY,
)


def install_categorical_data(ctx):
    ctx = ctx.child()
    conn = boto3.resource("s3", region_name="us-west-2")

    try:
        conn.create_bucket(Bucket=TAAR_SIMILARITY_BUCKET)
    except Exception:
        pass

    conn.Object(TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY).put(
        Body=json.dumps({"test": "donor_key"})
    )

    ctx["similarity_donors_pool"] = LazyJSONLoader(
        ctx, TAAR_SIMILARITY_BUCKET, TAAR_SIMILARITY_DONOR_KEY
    )

    return ctx


@mock_s3
def test_does_it_load(test_ctx):
    ctx = install_categorical_data(test_ctx)

    jdata, status = ctx["similarity_donors_pool"].get()
    assert jdata["test"] == "donor_key"
    check_jdata_status(jdata, status)


@mock_s3
def test_can_pickle(test_ctx):
    ctx = install_categorical_data(test_ctx)

    lazy_inst = ctx["similarity_donors_pool"]
    lazy_pickle = pickle.dumps(lazy_inst)
    lazy_inst2 = pickle.loads(lazy_pickle)


@mock_s3
def test_cached_load(test_ctx):
    ctx = install_categorical_data(test_ctx)
    loader = ctx["similarity_donors_pool"]
    jdata, status = loader.get()
    check_jdata_status(jdata, status)
    jdata, status = loader.get()
    assert not status


@mock_s3
def test_reload_on_expiry(test_ctx):
    ctx = install_categorical_data(test_ctx)
    loader = ctx["similarity_donors_pool"]

    jdata, status = loader.get()
    check_jdata_status(jdata, status)
    jdata, status = loader.get()
    assert not status

    # Force expirty time to be 10 seconds ago
    loader._expiry_time = loader._clock.time() - 10

    jdata, status = loader.get()
    check_jdata_status(jdata, status)


@mock_s3
def test_force_expiry(test_ctx):
    ctx = install_categorical_data(test_ctx)
    loader = ctx["similarity_donors_pool"]

    jdata, status = loader.get()
    check_jdata_status(jdata, status)
    jdata, status = loader.get()
    assert not status

    # Force expirty time to be 10 seconds ago
    loader.force_expiry()

    jdata, status = loader.get()
    check_jdata_status(jdata, status)


def check_jdata_status(jdata, status):
    assert jdata == {'test': 'donor_key'}
    assert status
