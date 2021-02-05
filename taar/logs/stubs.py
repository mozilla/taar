from sys import exc_info

from taar.interfaces import IMozLogging


class EmergencyLogger:
    """
    We need this one to get rid of python logging dependency in Ensemble spark job
     (see more detailed explanation in readme).
    It uses only print and logs only errors and warnings
    """
    def debug(self, msg, *args, **kwags):
        pass

    def info(self, msg, *args, **kwags):
        pass

    def warn(self, msg, *args, **kwags):
        print(f'WARN: {msg}')

    def warning(self, msg, *args, **kwags):
        self.warn(msg)

    def error(self, msg, e=None, *args, **kwags):
        print(f'ERROR: {msg}, {e or exc_info()}')

    def exception(self, msg, *args, **kwargs):
        self.error(msg, *args, **kwargs)


class LoggingStub(IMozLogging):
    def __init__(self, ctx):
        pass

    def get_logger(self, name):
        return EmergencyLogger()

    def set_log_level(self, level):
        pass
