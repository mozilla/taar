# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Context
"""
from taar.context import Context


def test_context():
    ctx = Context()
    ctx['foo'] = 42
    child_ctx = ctx.child()
    assert child_ctx['foo'] == 42

    # Now clobber the local context, and demonstrate
    # that we haven't touched the parent
    child_ctx['foo'] = 'bar'
    assert child_ctx['foo'] == 'bar'
    assert child_ctx.get('foo', 'batz') == 'bar'
    assert ctx['foo'] == 42
    assert ctx.get('foo', 'bar') == 42

    # Revert the child back to the parent value
    del child_ctx['foo']
    assert child_ctx['foo'] == 42

    # Defaults work as expected
    assert child_ctx.get('foo', 'bar') == 42
