from taar.profile_fetcher import ProfileFetcher
from taar import hbase_client


def get_client_profile_mock(*args, **kwargs):
    return {
        u'scalar_parent_browser_engagement_total_uri_count': 791,
        u'city': u'Rome',
        u'scalar_parent_browser_engagement_tab_open_event_count': 46,
        u'subsession_start_date': u'2017-09-20T10:00:00.0+02:00',
        u'subsession_length': 3785,
        u'places_bookmarks_count': 0,
        u'scalar_parent_browser_engagement_unique_domains_count': 11,
        u'os': u'Windows_NT',
        u'active_addons': [
            {u'addon_id': u'e10srollout@mozilla.org'},
            {u'addon_id': u'firefox@getpocket.com'},
            {u'addon_id': u'webcompat@mozilla.org', u'is_system': True},
        ],
        u'locale': 'it-IT'
    }


def test_profile_fetcher_returns_dict(monkeypatch):
    monkeypatch.setattr(hbase_client.HBaseClient,
                        'get_client_profile',
                        get_client_profile_mock)

    monkeypatch.setattr(hbase_client.HBaseClient,
                        '_get_hbase_hostname',
                        lambda x: 'master-ip-address')

    fetcher = ProfileFetcher()

    assert fetcher.get("random-client-id") == {
        "bookmark_count": 0,
        "disabled_addons_ids": [],
        "geo_city": "Rome",
        "os": "Windows_NT",
        "subsession_length": 3785,
        "tab_open_count": 46,
        "total_uri": 791,
        "unique_tlds": 11,
        "installed_addons": [
            "e10srollout@mozilla.org",
            "firefox@getpocket.com"
        ],
        "locale": "it-IT"
    }


def test_profile_fetcher_returns_none(monkeypatch):
    monkeypatch.setattr(hbase_client.HBaseClient,
                        'get_client_profile',
                        lambda x, y: None)

    monkeypatch.setattr(hbase_client.HBaseClient,
                        '_get_hbase_hostname',
                        lambda x: 'master-ip-address')

    fetcher = ProfileFetcher()

    assert fetcher.get("random-client-id") is None
