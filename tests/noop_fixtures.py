"""

Noop helpers
"""

import mock
from taar.recommenders.redis_cache import TAARCacheRedis


def noop_taarlite_dataload(stack):
    # no-op the taarlite rankdata
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_rank_data", return_value=None)
    )
    # no-op the taarlite guidguid data
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_coinstall_data", return_value=None, )
    )
    return stack


def noop_taarlocale_dataload(stack):
    # no-op the taarlite rankdata
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_locale_data", return_value=None)
    )
    return stack


def noop_taarcollab_dataload(stack):
    # no-op the taar collab
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_collab_data", return_value=None)
    )
    return stack


def noop_taarsimilarity_dataload(stack):
    # no-op the taar collab
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_similarity_data", return_value=None)
    )
    return stack


def noop_taarensemble_dataload(stack):
    # no-op the taar collab
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_ensemble_data", return_value=None)
    )
    stack.enter_context(
        mock.patch.object(TAARCacheRedis, "_update_whitelist_data", return_value=None)
    )
    return stack
