from decouple import config

TAAR_ENSEMBLE_BUCKET = config("TAAR_ENSEMBLE_BUCKET", default="test_ensemble_bucket")
TAAR_ENSEMBLE_KEY = config("TAAR_ENSEMBLE_KEY", default="test_ensemble_key")

TAAR_WHITELIST_BUCKET = config("TAAR_WHITELIST_BUCKET", default="test_whitelist_bucket")
TAAR_WHITELIST_KEY = config("TAAR_WHITELIST_KEY", default="test_whitelist_key")

TAAR_ITEM_MATRIX_BUCKET = config(
    "TAAR_ITEM_MATRIX_BUCKET", default="test_matrix_bucket"
)
TAAR_ITEM_MATRIX_KEY = config("TAAR_ITEM_MATRIX_KEY", default="test_matrix_key")
TAAR_ADDON_MAPPING_BUCKET = config(
    "TAAR_ADDON_MAPPING_BUCKET", default="test_mapping_bucket"
)
TAAR_ADDON_MAPPING_KEY = config("TAAR_ADDON_MAPPING_KEY", default="test_mapping_key")

TAAR_LOCALE_BUCKET = config("TAAR_LOCALE_BUCKET", default="test_locale_bucket")
TAAR_LOCALE_KEY = config("TAAR_LOCALE_KEY", default="test_locale_key")


TAAR_SIMILARITY_BUCKET = config(
    "TAAR_SIMILARITY_BUCKET", default="test_similarity_bucket"
)
TAAR_SIMILARITY_DONOR_KEY = config(
    "TAAR_SIMILARITY_DONOR_KEY", default="test_similarity_donor_key"
)
TAAR_SIMILARITY_LRCURVES_KEY = config(
    "TAAR_SIMILARITY_LRCURVES_KEY", default="test_similarity_lrcurves_key"
)

TAAR_EXPERIMENT_PROB = config("TAAR_EXPERIMENT_PROB", default=0.0)
TAAR_EXPERIMENT_LIMIT = config("TAAR_EXPERIMENT_LIMIT", default=15)
