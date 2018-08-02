"""
These are global fixtures automagically loaded by pytest
"""

import pytest
from srgutil.context import default_context
from srgutil.interfaces import IClock
from taar.cache import JSONCache, Clock

FAKE_LOCALE_DATA = {
    "te-ST": [
        "{1e6b8bce-7dc8-481c-9f19-123e41332b72}", "some-other@nice-addon.com",
        "{66d1eed2-a390-47cd-8215-016e9fa9cc55}", "{5f1594c3-0d4c-49dd-9182-4fbbb25131a7}"
    ],
    "en": [
        "some-uuid@test-addon.com", "other-addon@some-id.it"
    ]
}


class MockUtils:
    def get_s3_json_content(self, *args, **kwargs):
        return FAKE_LOCALE_DATA


@pytest.fixture
def test_ctx():
    ctx = default_context()
    ctx['utils'] = MockUtils()

    ctx[IClock] = Clock()
    ctx['clock'] = Clock()

    # TODO: replace this with the IS3Data interface
    ctx['cache'] = JSONCache(ctx)
    return ctx.child()
