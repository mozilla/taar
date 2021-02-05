# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# copy paste from https://github.com/mozilla/srgutil to get rid of this heavy legacy dependency
try:
    from abc import ABC
except Exception:
    from abc import ABCMeta

    class ABC(object):
        """Helper class that provides a standard way to create an ABC using
        inheritance.
        """
        __metaclass__ = ABCMeta
        __slots__ = ()


class IMozLogging(ABC):
    def get_logger(self, name):
        """Get a logger with the current configuration
        """

    def set_log_level(self, level):
        """Set the logs level, fox example 'DEBUG'
        """


class ITAARCache(ABC):
    def safe_load_data(self):
        raise NotImplementedError()

    def cache_context(self):
        raise NotImplementedError()
