
""" Custom logging utilities. """

import logging

import flask as fl

class PrefixedLogRecord(logging.LogRecord):

    """ A LogRecord subclass providing the `prefix` field containing the
    logger name, unless it's the root logger.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.prefix = "" if name == "root" else "[{}] ".format(name)

def setup_logging(level_str, extra_level_str):

    """ Set up logging with timestamped and prefixed log records, allowing
    log level differentiation for SQLAlchemy loggers.
    """

    level = getattr(logging, level_str.upper())

    extra_loggers = (
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
        "sqlalchemy.engine",
    )

    logging.setLogRecordFactory(make_log_record)
    logging.basicConfig(format="%(asctime)s %(levelname)7s: %(prefix)s%(message)s", level=level)

    if extra_level_str:
        extra_level = getattr(logging, extra_level_str.upper())

        for logger in extra_loggers:
            logging.getLogger(logger).setLevel(extra_level)

def make_log_record(name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None, **kwargs):

    """ LogRecord factory. Note that path is currently passed as None.
    Implement path name extraction when desired.
    """

    return PrefixedLogRecord(name, level, None, lno, msg, args, exc_info, func, sinfo)

def log_requests(app, make_log_string=None):

    """ Call with an application instance to register an `after_request`
    handler logging all requests.
    """

    def log_request(response):
        request = fl.request

        if make_log_string:
            message = make_log_string(request, response)
        else:
            message = (
                f"Completed {request.method} {request.path} for {request.remote_addr} "
                f"with {response.status}"
            )

        logging.info(message)

        return response

    app.after_request(log_request)
