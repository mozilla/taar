# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# copy paste from https://github.com/mozilla/srgutil to get rid of this heavy legacy dependency
from taar.logs.interfaces import IMozLogging
import logging.config
import sys


class ContextFilter(logging.Filter):
    """Enhances log messages with contextual information"""

    def __init__(self, logger, func):

        super().__init__()
        self._logger = logger
        self._func = func

    def filter(self, log_record):
        try:
            if self._func:
                self._func(log_record)
        except RuntimeError:
            pass

        return True

    def __enter__(self):
        self._logger.addFilter(self)

    def __exit__(self, type, value, traceback):
        self._logger.removeFilter(self)


class Logging(IMozLogging):
    LOG_NAME = 'srg'
    _log_config = {
        # Note that the formatters.json.logger_name must match
        # loggers.<logger_name> key
        'version': 1,
        'formatters': {
            'json': {
                '()': 'dockerflow.logging.JsonLogFormatter',
                'logger_name': LOG_NAME
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'json',
                'stream': sys.stdout
            },
        },

        'loggers': {
            LOG_NAME: {
                'handlers': ['console'],
                'level': 'INFO'
            },
        }
    }

    def __init__(self, ctx):
        self._ctx = ctx
        self._logger_prefix = ''
        self._apply_config()

    def set_log_level(self, log_level):
        self._log_config['loggers'][self.LOG_NAME]['level'] = log_level
        self._log_config['handlers']['console']['level'] = log_level
        self._apply_config()

    def _apply_config(self):
        self._logger_prefix = self._log_config['formatters']['json']['logger_name']
        logging.config.dictConfig(self._log_config)

    def get_logger(self, name):
        return logging.getLogger("%s.%s" % (self._logger_prefix, name))
