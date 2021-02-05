# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from decouple import config


class AppSettings:
    PYTHON_LOG_LEVEL = config("PYTHON_LOG_LEVEL", "INFO")
    STATSD_HOST = config("STATSD_HOST", default="localhost", cast=str)
    STATSD_PORT = config("STATSD_PORT", default=8125, cast=int)
    NO_REDIS = config("NO_REDIS", False, cast=bool)
    TAAR_MAX_RESULTS = config("TAAR_MAX_RESULTS", default=10, cast=int)

    TAARLITE_MAX_RESULTS = config("TAARLITE_MAX_RESULTS", default=4, cast=int)

    # Bigtable config
    BIGTABLE_PROJECT_ID = config(
        "BIGTABLE_PROJECT_ID", default="cfr-personalization-experiment"
    )
    BIGTABLE_INSTANCE_ID = config("BIGTABLE_INSTANCE_ID", default="taar-profile")
    BIGTABLE_TABLE_ID = config("BIGTABLE_TABLE_ID", default="taar_profile")


class DefaultCacheSettings:
    DISABLE_TAAR_LITE = config("DISABLE_TAAR_LITE", False, cast=bool)
    DISABLE_ENSEMBLE = config("DISABLE_ENSEMBLE", False, cast=bool)

    TAAR_ENSEMBLE_BUCKET = config("TAAR_ENSEMBLE_BUCKET", default="test_ensemble_bucket")
    TAAR_ENSEMBLE_KEY = config("TAAR_ENSEMBLE_KEY", default="test_ensemble_key")

    TAAR_WHITELIST_BUCKET = config("TAAR_WHITELIST_BUCKET", default="test_whitelist_bucket")
    TAAR_WHITELIST_KEY = config("TAAR_WHITELIST_KEY", default="test_whitelist_key")

    TAAR_ITEM_MATRIX_BUCKET = config("TAAR_ITEM_MATRIX_BUCKET", default="test_matrix_bucket")
    TAAR_ITEM_MATRIX_KEY = config("TAAR_ITEM_MATRIX_KEY", default="test_matrix_key")
    TAAR_ADDON_MAPPING_BUCKET = config("TAAR_ADDON_MAPPING_BUCKET", default="test_mapping_bucket")
    TAAR_ADDON_MAPPING_KEY = config("TAAR_ADDON_MAPPING_KEY", default="test_mapping_key")

    TAAR_LOCALE_BUCKET = config("TAAR_LOCALE_BUCKET", default="test_locale_bucket")
    TAAR_LOCALE_KEY = config("TAAR_LOCALE_KEY", default="test_locale_key")

    TAAR_SIMILARITY_BUCKET = config("TAAR_SIMILARITY_BUCKET", default="test_similarity_bucket")
    TAAR_SIMILARITY_DONOR_KEY = config("TAAR_SIMILARITY_DONOR_KEY", default="test_similarity_donor_key")
    TAAR_SIMILARITY_LRCURVES_KEY = config("TAAR_SIMILARITY_LRCURVES_KEY", default="test_similarity_lrcurves_key")

    # TAAR-lite configuration below

    TAARLITE_GUID_COINSTALL_BUCKET = config("TAARLITE_GUID_COINSTALL_BUCKET", "telemetry-parquet")
    TAARLITE_GUID_COINSTALL_KEY = config("TAARLITE_GUID_COINSTALL_KEY", "taar/lite/guid_coinstallation.json")

    TAARLITE_GUID_RANKING_KEY = config("TAARLITE_GUID_RANKING_KEY", "taar/lite/guid_install_ranking.json")

    TAARLITE_TRUNCATE = config("TAARLITE_TRUNCATE", AppSettings.TAARLITE_MAX_RESULTS * 5, cast=int)


class RedisCacheSettings(DefaultCacheSettings):
    # 4 hour liviliness for TAARLITE data
    TAARLITE_TTL = config("TAARLITE_TTL", 60 * 60 * 4, cast=int)

    # TAARlite needs redis backed mutex's to protect critical sections
    # Set a default TAARLite mutex TTL of 1 hour to fully populate the
    # redis cache
    TAARLITE_MUTEX_TTL = config("TAARLITE_MUTEX_TTL", 60 * 60, cast=int)

    REDIS_HOST = config("REDIS_HOST", "localhost", cast=str)
    REDIS_PORT = config("REDIS_PORT", 6379, cast=int)


class PackageCacheSettings(DefaultCacheSettings):
    TAAR_LOCALE_BUCKET = 'moz-fx-data-taar-pr-prod-e0f7-prod-models'
    TAAR_LOCALE_KEY = 'taar/locale/top10_dict.json.bz2'

    TAAR_SIMILARITY_BUCKET = 'moz-fx-data-taar-pr-prod-e0f7-prod-models'
    TAAR_SIMILARITY_DONOR_KEY = 'taar/similarity/donors.json.bz2'
    TAAR_SIMILARITY_LRCURVES_KEY = 'taar/similarity/lr_curves.json.bz2'

    TAAR_ITEM_MATRIX_BUCKET = 'moz-fx-data-taar-pr-prod-e0f7-prod-models'
    TAAR_ITEM_MATRIX_KEY = 'addon_recommender/item_matrix.json.bz2'
    TAAR_ADDON_MAPPING_BUCKET = 'moz-fx-data-taar-pr-prod-e0f7-prod-models'
    TAAR_ADDON_MAPPING_KEY = 'addon_recommender/addon_mapping.json.bz2'

    DISABLE_TAAR_LITE = True
    DISABLE_ENSEMBLE = True
