"""
Test that we can reorder (GUID, weight) tuples based on random
selection based on probability,
"""

from taar.recommenders.randomizer import reorder_guids
from taar.recommenders.randomizer import in_experiment

import numpy as np
from collections import Counter


def most_frequent(List):
    occurence_count = Counter(List)
    return occurence_count.most_common(1)[0][0]


def test_reorder_guids():
    # These weights are selected carefully so that they are different
    # enough that a randomized selection using the weighted inputs
    # will be stable 'enough' that we should be able to pass tests
    # consistently over a sufficiently large sample

    # Fix the random seed so that we get stable results between test
    # runs
    np.random.seed(seed=42)

    guid_weight_tuples = [
        ("guid0", -0.60),
        ("guid1", -0.30),
        ("guid2", 0.09),
        ("guid3", 0.30),
        ("guid4", 2.5),
    ]

    # Run this 100 times to get the average ordering
    results = []
    limit = 4
    for i in range(100):
        results.append(reorder_guids(guid_weight_tuples, size=limit))

    best_result = []
    for i in range(limit):
        best_result.append(most_frequent([row[i] for row in results])[0])

    assert best_result == ["guid4", "guid3", "guid2", "guid1"]


def test_reorder_guids_size_less_than_limit():
    guid_weight_tuples = [
        ("guid0", -0.60),
        ("guid1", -0.30)]
    limit = 4

    reordered = reorder_guids(guid_weight_tuples, size=limit)

    assert len(reordered) == 2


def test_experimental_branch_guid():
    """
    Test the experimental cutoff selection code.

    The evaluation should be stable for a given probability and
    client_id.
    """
    for i in range(10, 100, 10):
        id = hex(i)[2:]
        cutoff = (i + 9.0) / 100

        total = sum([in_experiment(id, cutoff) for i in range(100)])
        assert total == 100

        total = sum([in_experiment(id, cutoff - 0.1) for i in range(100)])
        assert total == 0


def test_in_experiment_zero_prob():
    """
    Test the edge case when some client IDs go to experiment even with 0 probability.
    """
    assert not in_experiment('0ace1ca2a3519332ab93e76a049fe74091fa8fc9063399caa8545dd23f93de5c', xp_prob=0.0)
