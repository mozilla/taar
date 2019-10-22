# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
This module re-orders the (GUID, weight) 2-tuples using
numpy.random.choice
"""

import numpy as np


def in_experiment(client_id, xp_prob=0.5):
    """
    Return whether or not this client_id is in the experiment.

    xp_prob should be a probability between 0.0 and 1.0 which is the
    chance that the experimental branch is selected.
    """
    # Strip out anything that's not a hex value so we can safely
    # convert from base16 (hex) to base10
    hex_client = ''.join([c for c in client_id if c.lower() in 'abcdef0123456789'])
    int_client = int(hex_client, 16)
    return int((int_client % 100) <= (xp_prob * 100))


def reorder_guids(guid_weight_tuples, size=None):
    """
    This reorders (GUID, weight) 2-tuples based on the weight using
    random selection, without replacement.

    @size denotes the length of the output.  If size exceeds the
    length of the tuples, the underlying numpy function will throw an
    error.
    """
    weight_list = [weight for (guid, weight) in guid_weight_tuples]
    guids = [guid for (guid, weight) in guid_weight_tuples]
    guid_map = dict(zip(guids, guid_weight_tuples))

    if size is None:
        size = len(guids)

    # Normalize the weights so that they're probabilities
    total_weight = sum(weight_list)
    probabilities = [w * 1.0 / total_weight for w in weight_list]

    choices = np.random.choice(guids, size=size, replace=False, p=probabilities)
    return [guid_map[guid] for guid in choices]
