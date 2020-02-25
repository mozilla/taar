"""
These are global fixtures automagically loaded by pytest
"""

import pytest
from srgutil.context import default_context
from srgutil.interfaces import IClock

FAKE_LOCALE_DATA = {
    "te-ST": [
        "{1e6b8bce-7dc8-481c-9f19-123e41332b72}", "some-other@nice-addon.com",
        "{66d1eed2-a390-47cd-8215-016e9fa9cc55}", "{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}"
    ],
    "en": [
        "some-uuid@test-addon.com", "other-addon@some-id.it"
    ]
}


@pytest.fixture
def test_ctx():
    ctx = default_context()
    ctx.set('clock', ctx.get(IClock))
    return ctx
