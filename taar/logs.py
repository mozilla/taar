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

import logging.config


class IMozLogging(ABC):
    def set_config(self, cfg):
        """Override the default configuration of the logging system
        """

    def get_logger(self, name):
        """Get a logger with the current configuration
        """

    def get_prefix(self):
        """Get the logger prefix name
        """


class Logging(IMozLogging):
    _log_config = {
        # Note that the formatters.json.logger_name must match
        # loggers.<logger_name> key
        'version': 1,
        'formatters': {
            'json': {
                '()': 'dockerflow.logging.JsonLogFormatter',
                'logger_name': 'srg'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'json'
            },
        },
        'loggers': {
            'srg': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        }
    }

    def __init__(self, ctx):
        self._ctx = ctx
        self._logger_prefix = ''
        self._apply_config()

    def set_config(self, cfg):
        self._log_config = cfg

    def set_prefix(self, prefix, log_level):
        self._log_config['formatters']['json']['logger_name'] = prefix
        self._log_config['loggers'][prefix] = {'handlers': ['console'], 'level': log_level}
        self._log_config['handlers']['console']['level'] = log_level
        self._apply_config()

    def get_prefix(self):
        return self._logger_prefix

    def _apply_config(self):
        self._logger_prefix = self._log_config['formatters']['json']['logger_name']
        logging.config.dictConfig(self._log_config)

    def get_logger(self, name):
        return logging.getLogger("%s.%s" % (self._logger_prefix, name))
