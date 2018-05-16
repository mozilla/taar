from .profile_fetcher import ProfileFetcher     # noqa
from .adapters.dynamo import ProfileController  # noqa
import pkg_resources

__version__ = pkg_resources.require("mozilla-taar3")[0].version
