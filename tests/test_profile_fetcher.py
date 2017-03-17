from taar.profile_fetcher import ProfileFetcher
from taar import hbase_client


def get_client_addons_mock(*args, **kwargs):
    return {
        u'active_addons': [
            {u'addon_id': u'e10srollout@mozilla.org'},
            {u'addon_id': u'firefox@getpocket.com'}
        ]
    }


def test_profile_fetcher_returns_dict(monkeypatch):
    monkeypatch.setattr(hbase_client.HBaseClient,
                        'get_client_addons',
                        get_client_addons_mock)

    monkeypatch.setattr(hbase_client.HBaseClient,
                        '_get_master_address',
                        lambda x: 'master-ip-address')

    fetcher = ProfileFetcher()

    fetcher.get("random-client-id") == {
        "installed_addons": [
            "e10srollout@mozilla.org",
            "firefox@getpocket.com"
        ],
    }
