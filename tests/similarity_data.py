# Each of these records is identical with respect to the
# CATEGORICAL_FEATURES and CONTINUOUS_FEATURES of the TAAR client
# generated by `generate_a_fake_taar_client` except for the
# `total_uri` field.  This gives us a deterministic way to order the
# recommendations provided by the SimilarityRecommender based on
# continuous feature similarity.

CONTINUOUS_FEATURE_FIXTURE_DATA = [
    {
        "active_addons": [
            "{test-guid-1}",
            "{test-guid-2}",
            "{test-guid-3}",
            "{test-guid-4}",
        ],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 190,
        "unique_tlds": 21,
    },
    {
        "active_addons": [
            "{test-guid-5}",
            "{test-guid-6}",
            "{test-guid-1}",
            "{test-guid-8}",
        ],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 200,
        "unique_tlds": 21,
    },
    {
        "active_addons": [
            "{test-guid-9}",
            "{test-guid-10}",
            "{test-guid-11}",
            "{test-guid-12}",
        ],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    },
    {
        "active_addons": ["{test-guid-13}", "{test-guid-14}"],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 210,
        "unique_tlds": 21,
    },
]

# Match the fixture taar client, but vary the geo_city to test only
# the categorical feature matching.

# Additionally the second donor contains the only duplicate recommendation
# of "{test-guid-1}"

CATEGORICAL_FEATURE_FIXTURE_DATA = [
    {
        "active_addons": [
            "{test-guid-1}",
            "{test-guid-2}",
            "{test-guid-3}",
            "{test-guid-4}",
        ],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    },
    {
        # "{test-guid-1}" appears in duplicate here.
        "active_addons": [
            "{test-guid-5}",
            "{test-guid-6}",
            "{test-guid-1}",
            "{test-guid-8}",
        ],
        "geo_city": "toronto-ca",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    },
    {
        "active_addons": [
            "{test-guid-9}",
            "{test-guid-10}",
            "{test-guid-11}",
            "{test-guid-12}",
        ],
        "geo_city": "brasilia-br",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    },
    {
        "active_addons": ["{test-guid-13}", "{test-guid-1}"],
        "geo_city": "toronto-ca",
        "subsession_length": 4911,
        "locale": "br-PT",
        "os": "mac",
        "bookmark_count": 7,
        "tab_open_count": 4,
        "total_uri": 222,
        "unique_tlds": 21,
    },
]
