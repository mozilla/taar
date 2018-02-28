from taar import ProfileFetcher


class MockProfileController:
    def __init__(self, mock_profile):
        self._profile = mock_profile

    def get_client_profile(self, client_id):
        return self._profile


def test_profile_fetcher_returns_dict():
    mock_data = {u'scalar_parent_browser_engagement_total_uri_count': 791,
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
                 u'locale': 'it-IT'}
    mock_profile_controller = MockProfileController(mock_data)
    fetcher = ProfileFetcher(mock_profile_controller)

    # Note that active_addons in the raw JSON source is remapped to
    # 'installed_addons'
    assert fetcher.get("random-client-id") == {
        "client_id": 'random-client-id',
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


def test_profile_fetcher_returns_none():
    fetcher = ProfileFetcher(MockProfileController(None))
    assert fetcher.get("random-client-id") is None
