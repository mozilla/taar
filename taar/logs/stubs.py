from taar.logs.interfaces import IMozLogging


class LoggerStub:
    def debug(self, *args, **kwags):
        pass

    def info(self, *args, **kwags):
        pass

    def warn(self, *args, **kwags):
        pass

    def warning(self, *args, **kwags):
        pass

    def error(self, *args, **kwags):
        pass


class LoggingStub(IMozLogging):
    def __init__(self, ctx):
        pass

    def get_logger(self, name):
        return LoggerStub()

    def set_log_level(self, level):
        pass

