# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from taar.profile_fetcher import ProfileFetcher
from taar.profile_fetcher import BigTableProfileController
from google.cloud import bigtable
import copy
import json
import zlib
from mock import MagicMock


class MockProfileController:
    def __init__(self, mock_profile):
        self._profile = mock_profile

    def get_client_profile(self, client_id):
        return self._profile


def test_profile_fetcher_returns_none(test_ctx):
    fetcher = ProfileFetcher(test_ctx)
    fetcher.set_client(MockProfileController(None))
    assert fetcher.get("random-client-id") is None


MOCK_DATA = {
    "profile": {
        u"scalar_parent_browser_engagement_total_uri_count": 791,
        u"city": u"Rome",
        u"scalar_parent_browser_engagement_tab_open_event_count": 46,
        u"subsession_start_date": u"2017-09-20T10:00:00.0+02:00",
        u"subsession_length": 3785,
        u"places_bookmarks_count": 0,
        u"scalar_parent_browser_engagement_unique_domains_count": 11,
        u"os": u"Windows_NT",
        u"active_addons": [
            {u"addon_id": u"e10srollout@mozilla.org"},
            {u"addon_id": u"firefox@getpocket.com"},
            {u"addon_id": u"webcompat@mozilla.org", "is_system": True},
        ],
        u"locale": "it-IT",
    },
    "expected_result": {
        "client_id": "random-client-id",
        "bookmark_count": 0,
        "disabled_addons_ids": [],
        "geo_city": "Rome",
        "os": "Windows_NT",
        "subsession_length": 3785,
        "tab_open_count": 46,
        "total_uri": 791,
        "unique_tlds": 11,
        "installed_addons": ["e10srollout@mozilla.org", "firefox@getpocket.com",],
        "locale": "it-IT",
    },
}


def test_profile_fetcher_returns_dict(test_ctx):
    fetcher = ProfileFetcher(test_ctx)

    mock_data = MOCK_DATA["profile"]
    mock_profile_controller = MockProfileController(mock_data)
    fetcher.set_client(mock_profile_controller)

    # Note that active_addons in the raw JSON source is remapped to
    # 'installed_addons'
    assert fetcher.get("random-client-id") == MOCK_DATA["expected_result"]


def test_dont_crash_without_active_addons(test_ctx):
    mock_data = copy.deepcopy(MOCK_DATA["profile"])
    del mock_data["active_addons"]
    mock_profile_controller = MockProfileController(mock_data)

    fetcher = ProfileFetcher(test_ctx)
    fetcher.set_client(mock_profile_controller)

    expected = copy.deepcopy(MOCK_DATA["expected_result"])
    expected["installed_addons"][:] = []
    assert fetcher.get("random-client-id") == expected


def test_crashy_profile_controller(test_ctx, monkeypatch):
    def mock_bigtable_client(*args, **kwargs):
        class MockClient:
            def __init__(self, *args, **kwargs):
                pass

            def instance(self, *args, **kwargs):
                return MagicMock()

        return MockClient

    monkeypatch.setattr(bigtable, "Client", mock_bigtable_client)

    pc = BigTableProfileController(
        test_ctx, "mock_project_id", "mock_instance_id", "mock_table_id"
    )
    assert pc.get_client_profile("exception_raising_client_id") is None


def test_profile_controller(test_ctx, monkeypatch):
    class MockCell:
        client_profile = {"key": "with_some_data"}
        value = zlib.compress(json.dumps(client_profile).encode("utf8"))

    mc = MockCell()

    def mock_bigtable_client(*args, **kwargs):
        class MockTable:
            def __init__(self, table_id):
                pass

            def read_row(self, *args, **kwargs):
                class MockRow:
                    @property
                    def cells(self):
                        magic_cn = MagicMock()
                        magic_cn.__getitem__.return_value = mc

                        magic_cf = MagicMock()
                        magic_cf.__getitem__.return_value = magic_cn

                        mm = MagicMock()
                        mm.__getitem__.return_value = magic_cf
                        return mm

                return MockRow()

        class MockInstance:
            def table(self, table_id):
                return MockTable(table_id)

        class MockClient:
            def instance(self, *args, **kwargs):
                return MockInstance(*args, **kwargs)

        return MockClient

    monkeypatch.setattr(bigtable, "Client", mock_bigtable_client)

    pc = BigTableProfileController(
        test_ctx, "mock_project_id", "mock_instance_id", "mock_table_id"
    )
    jdata = pc.get_client_profile("a_mock_client")
    assert jdata == {"key": "with_some_data"}


def test_profile_controller_no_user(test_ctx, monkeypatch):
    def mock_bigtable_client(*args, **kwargs):
        class MockTable:
            def __init__(self, table_id):
                pass

            def read_row(self, *args, **kwargs):
                return None

        class MockInstance:
            def table(self, table_id):
                return MockTable(table_id)

        class MockClient:
            def instance(self, *args, **kwargs):
                return MockInstance(*args, **kwargs)

        return MockClient

    monkeypatch.setattr(bigtable, "Client", mock_bigtable_client)

    pc = BigTableProfileController(
        test_ctx, "mock_project_id", "mock_instance_id", "mock_table_id"
    )
    jdata = pc.get_client_profile("a_mock_client")
    assert jdata is None
