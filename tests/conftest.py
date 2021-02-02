"""
These are global fixtures automagically loaded by pytest
"""

import pytest
from taar.context import _default_context
from taar.recommenders.redis_cache import TAARCacheRedis

FAKE_LOCALE_DATA = {
    "te-ST": [
        "{1e6b8bce-7dc8-481c-9f19-123e41332b72}",
        "some-other@nice-addon.com",
        "{66d1eed2-a390-47cd-8215-016e9fa9cc55}",
        "{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}",
    ],
    "en": ["some-uuid@test-addon.com", "other-addon@some-id.it"],
}


@pytest.fixture(scope='function')
def test_ctx():
    ctx = _default_context(TAARCacheRedis)
    return ctx


@pytest.fixture
def TAARLITE_MOCK_DATA():
    return {
        "guid-1": {
            "guid-2": 1000,
            "guid-3": 100,
            "guid-4": 10,
            "guid-5": 1,
            "guid-6": 1,
        },
        "guid-2": {
            "guid-1": 50,
            "guid-3": 40,
            "guid-4": 20,
            "guid-8": 30,
            "guid-9": 10,
        },
        "guid-3": {"guid-1": 100, "guid-2": 40, "guid-4": 70},
        "guid-4": {"guid-2": 20},
        "guid-6": {"guid-1": 5, "guid-7": 100, "guid-8": 100, "guid-9": 100},
        "guid-8": {"guid-2": 30},
        "guid-9": {"guid-2": 10},
    }


@pytest.fixture
def TAARLITE_TIE_MOCK_DATA():
    return {
        "guid-1": {"guid-2": 100, "guid-3": 100, "guid-4": 100, "guid-5": 100},
        "guid-2": {"guid-1": 100, "guid-3": 100, "guid-4": 100, "guid-5": 100},
        "guid-3": {"guid-1": 100, "guid-2": 100, "guid-4": 100, "guid-5": 100},
        "guid-4": {"guid-1": 20, "guid-2": 20, "guid-3": 20, "guid-5": 20},
        "guid-5": {"guid-1": 20, "guid-2": 20, "guid-3": 20, "guid-4": 20},
    }


@pytest.fixture
def TAARLITE_MOCK_GUID_RANKING():
    return {
        "guid-1": 10,
        "guid-2": 9,
        "guid-3": 8,
        "guid-4": 7,
        "guid-5": 6,
        "guid-6": 5,
        "guid-7": 4,
        "guid-8": 3,
        "guid-9": 2,
    }


@pytest.fixture
def TAARLITE_CUTOFF_GUID_RANKING():
    return {
        "guid-1": 10000,
        "guid-2": 9000,
        "guid-3": 8000,
        "guid-4": 7,
        "guid-5": 6000,
        "guid-6": 5000,
        "guid-7": 4000,
        "guid-8": 3000,
        "guid-9": 2000,
    }
