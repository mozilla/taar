from pkg_resources import get_distribution
from .profile_fetcher import ProfileFetcher     # noqa
from .adapters.dynamo import ProfileController  # noqa

__version__ = get_distribution('mozilla-taar3').version
