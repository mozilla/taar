"""
This module re-orders the (GUID, weight) 2-tuples using
numpy.random.choice
"""

import numpy as np


def in_experiment(client_id, xp_prob=0.5):
    """
    Return whether or not this client_id is in the experiment.

    xp_prob is a probability between 0.0 and 1.0 which is the
    chance that the experimental branch is selected.
    """
    hex_client = "".join([c for c in client_id.lower() if c in "abcdef0123456789"])
    int_client = int(hex_client, 16)
    return int((int_client % 100) < (xp_prob * 100))


def reorder_guids(guid_weight_tuples, size=None):
    """
    This reorders (GUID, weight) 2-tuples based on the weight using
    random selection, without replacement.

    @size denotes the length of the output.
    """
    if guid_weight_tuples is None or len(guid_weight_tuples) == 0:
        return []

    weights = np.array([weight for (guid, weight) in guid_weight_tuples])
    guids = [guid for (guid, weight) in guid_weight_tuples]
    guid_map = dict(zip(guids, guid_weight_tuples))

    if size is None:
        size = len(guids)
    else:
        size = min(size, len(guids))

    # Normalize the weights so that they're probabilities
    # Scale first, weights can be negative (for example, collaborative filtering similarity scores)
    scaled_weights = weights - np.min(weights) + np.finfo(float).eps
    probabilities = scaled_weights / np.sum(scaled_weights)

    choices = np.random.choice(guids, size=size, replace=False, p=probabilities)
    return [guid_map[guid] for guid in choices]
