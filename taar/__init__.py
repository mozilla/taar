from .profile_fetcher import ProfileFetcher     # noqa
import pkg_resources

__version__ = pkg_resources.require("mozilla-taar3")[0].version
