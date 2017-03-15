from taar.profile_fetcher import ProfileFetcher


def test_profile_fetcher_returns_dict():
    fetcher = ProfileFetcher()

    fetcher.get("random-client-id") == {
        "installed_addons": [
            "uBlock0@raymondhill.net",
        ],
    }
