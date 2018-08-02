# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar import ProfileFetcher
from taar.profile_fetcher import ProfileController
import boto3
import copy
import json
import zlib


class MockProfileController:
    def __init__(self, mock_profile):
        self._profile = mock_profile

    def get_client_profile(self, client_id):
        return self._profile


def test_profile_fetcher_returns_none(test_ctx):
    fetcher = ProfileFetcher(test_ctx)
    fetcher.set_client(MockProfileController(None))
    assert fetcher.get("random-client-id") is None


MOCK_DATA = {'profile': {u'scalar_parent_browser_engagement_total_uri_count': 791,
                         u'city': u'Rome',
                         u'scalar_parent_browser_engagement_tab_open_event_count': 46,
                         u'subsession_start_date': u'2017-09-20T10:00:00.0+02:00',
                         u'subsession_length': 3785,
                         u'places_bookmarks_count': 0,
                         u'scalar_parent_browser_engagement_unique_domains_count': 11,
                         u'os': u'Windows_NT',
                         u'active_addons': [{u'addon_id': u'e10srollout@mozilla.org'},
                                            {u'addon_id': u'firefox@getpocket.com'},
                                            {u'addon_id': u'webcompat@mozilla.org', 'is_system': True}],
                         u'locale': 'it-IT'},
             'expected_result': {"client_id": 'random-client-id',
                                 "bookmark_count": 0,
                                 "disabled_addons_ids": [],
                                 "geo_city": "Rome",
                                 "os": "Windows_NT",
                                 "subsession_length": 3785,
                                 "tab_open_count": 46,
                                 "total_uri": 791,
                                 "unique_tlds": 11,
                                 "installed_addons": ["e10srollout@mozilla.org",
                                                      "firefox@getpocket.com"],
                                 "locale": "it-IT"}
             }


def test_profile_fetcher_returns_dict(test_ctx):
    fetcher = ProfileFetcher(test_ctx)

    mock_data = MOCK_DATA['profile']
    mock_profile_controller = MockProfileController(mock_data)
    fetcher.set_client(mock_profile_controller)

    # Note that active_addons in the raw JSON source is remapped to
    # 'installed_addons'
    assert fetcher.get("random-client-id") == MOCK_DATA['expected_result']


def test_dont_crash_without_active_addons(test_ctx):
    mock_data = copy.deepcopy(MOCK_DATA['profile'])
    del mock_data['active_addons']
    mock_profile_controller = MockProfileController(mock_data)

    fetcher = ProfileFetcher(test_ctx)
    fetcher.set_client(mock_profile_controller)

    expected = copy.deepcopy(MOCK_DATA['expected_result'])
    expected['installed_addons'][:] = []
    assert fetcher.get("random-client-id") == expected


def test_crashy_profile_controller(test_ctx, monkeypatch):
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

    pc = ProfileController(test_ctx, 'us-west-2', 'taar_addon_data_20180206')
    assert pc.get_client_profile("exception_raising_client_id") is None


def test_profile_controller(test_ctx, monkeypatch):
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

    pc = ProfileController(test_ctx, 'us-west-2', 'taar_addon_data_20180206')
    jdata = pc.get_client_profile("exception_raising_client_id")
    assert jdata == {'key': 'with_some_data'}
