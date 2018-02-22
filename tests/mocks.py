# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


class MockRecommender:
    """The MockRecommender takes in a map of GUID->weight."""

    def __init__(self, guid_map):
        self._guid_map = guid_map

    def can_recommend(self, *args, **kwargs):
        return True

    def recommend(self, *args, **kwargs):
        return sorted(self._guid_map.items(), key=lambda item: -item[1])


class MockRecommenderFactory:
    """
    A RecommenderFactory provides support to create recommenders.

    The existence of a factory enables injection of dependencies into
    the RecommendationManager and eases the implementation of test
    harnesses.
    """
    def __init__(self, **kwargs):
        mock_legacy = MockRecommender({'abc': 1.0, 'bcd': 1.1, 'cde': 1.2})
        mock_locale = MockRecommender({'def': 2.0, 'efg': 2.1, 'fgh': 2.2, 'abc': 2.3})
        mock_collaborative = MockRecommender({'ghi': 3.0, 'hij': 3.1, 'ijk': 3.2, 'def': 3.3})
        mock_similarity = MockRecommender({'jkl': 4.0,  'klm': 4.1, 'lmn': 4.2, 'ghi': 4.3})

        self._recommender_factory_map = {'legacy': lambda: mock_legacy,
                                         'collaborative': lambda: mock_collaborative,
                                         'similarity': lambda: mock_similarity,
                                         'locale': lambda: mock_locale}

        # Clobber any kwarg passed in recommenders
        for key in self._recommender_factory_map.keys():
            self._recommender_factory_map[key] = kwargs.get(key, self._recommender_factory_map[key])

    def get_names(self):
        return self._recommender_factory_map.keys()

    def create(self, recommender_name):
        return self._recommender_factory_map[recommender_name]()


class MockProfileController:
    def __init__(self, mock_profile):
        self._profile = mock_profile

    def get_client_profile(self, client_id):
        return self._profile
