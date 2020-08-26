import json
from mock import patch
from taar.recommenders.redis_cache import AddonsCoinstallCache
import os.path

FIXTURE_PATH = os.path.join(os.path.split(os.path.realpath(__file__))[0], "fixtures")

COINSTALL_PATH = os.path.join(FIXTURE_PATH, "guid_coinstallation.json")
RANK_PATH = os.path.join(FIXTURE_PATH, "guid-ranking.json")

GUID_COINSTALL = json.load(open(COINSTALL_PATH, "r"))
GUID_RANK = json.load(open(RANK_PATH, "r"))


def test_coinstall_create(test_ctx):

    with patch.object(AddonsCoinstallCache, "fetch_ranking_data") as mock_ranking_data:
        mock_ranking_data.return_value = GUID_RANK
        with patch.object(
            AddonsCoinstallCache, "fetch_coinstall_data"
        ) as mock_coinstall_data:
            mock_coinstall_data.return_value = GUID_COINSTALL
            _ = AddonsCoinstallCache(test_ctx)
