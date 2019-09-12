# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
These are fixtures that are used for testing TAAR in a production
enviroment with known stable client_ids
"""

import hashlib


def hasher(client_id):
    return hashlib.new("sha256", client_id.encode("utf8")).hexdigest()


# These clients should have suggestions returned
TEST_CLIENT_IDS = [
    hasher("00000000-0000-0000-0000-000000000000"),
    hasher("11111111-1111-1111-1111-111111111111"),
    hasher("22222222-2222-2222-2222-222222222222"),
    hasher("33333333-3333-3333-3333-333333333333"),
]

# These clients should have no profile information and should fail at
# returning any kind of result
EMPTY_TEST_CLIENT_IDS = [
    hasher("00000000-aaaa-0000-0000-000000000000"),
    hasher("11111111-aaaa-1111-1111-111111111111"),
    hasher("22222222-aaaa-2222-2222-222222222222"),
    hasher("33333333-aaaa-3333-3333-333333333333"),
]
