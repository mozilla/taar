"""
Test that we can reorder (GUID, weight) tuples based on random
selection based on probability,
"""

from taar.recommenders.randomizer import reorder_guids
from taar.recommenders.randomizer import in_experiment


def test_reorder_guids():
    guid_weight_tuples = [
        ("guid1", 0.1),
        ("guid2", 0.2),
        ("guid3", 0.3),
        ("guid4", 0.4),
    ]
    actual = reorder_guids(guid_weight_tuples)
    print(actual)


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
