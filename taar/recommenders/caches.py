import sys


def warm_caches():
    if "pytest" in sys.modules:
        # Don't warm caches up under test
        return

    from taar.recommenders.guid_based_recommender import (
        GuidCoinstall,
        GuidRanking,
    )

    guid_coinstall = GuidCoinstall.get_instance()
    guid_rank = GuidRanking.get_instance()
    guid_coinstall.block_until_cached()
    guid_rank.block_until_cached()
