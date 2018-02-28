
from taar.adapters.dynamo import ProfileController
import boto3
import zlib
import json


def test_crashy_profile_controller(monkeypatch):
    def mock_boto3_resource(*args, **kwargs):
        class ExceptionRaisingMockTable:
            def __init__(self, tbl_name):
                pass

            def get_item(self, *args, **kwargs):
                raise Exception

        class MockDDB:
            pass
        mock_ddb = MockDDB()
        mock_ddb.Table = ExceptionRaisingMockTable
        return mock_ddb

    monkeypatch.setattr(boto3, 'resource', mock_boto3_resource)

    pc = ProfileController('us-west-2', 'taar_addon_data_20180206')
    assert pc.get_client_profile("exception_raising_client_id") is None


def test_profile_controller(monkeypatch):
    def mock_boto3_resource(*args, **kwargs):
        some_bytes = zlib.compress(json.dumps({'key': "with_some_data"}).encode('utf8'))

        class ValueObj:
            value = some_bytes

        class MockTable:
            def __init__(self, tbl_name):
                pass

            def get_item(self, *args, **kwargs):
                value_obj = ValueObj()
                response = {'Item': {'json_payload': value_obj}}
                return response

        class MockDDB:
            pass
        mock_ddb = MockDDB()
        mock_ddb.Table = MockTable
        return mock_ddb

    monkeypatch.setattr(boto3, 'resource', mock_boto3_resource)

    pc = ProfileController('us-west-2', 'taar_addon_data_20180206')
    jdata = pc.get_client_profile("exception_raising_client_id")
    assert jdata == {'key': 'with_some_data'}
