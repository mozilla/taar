# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib


def hasher(client_id):
    return hashlib.new("sha256", client_id.encode("utf8")).hexdigest()
