
""" Custom logging utilities. """

import logging

from functools import partial

import flask as fl

class PrefixedLogRecord(logging.LogRecord):

    """ A LogRecord subclass providing the `prefix` field containing the
    logger name, unless it's the root logger.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.prefix = "" if name == "root" else "[{}] ".format(name)

class MultilineLogRecord(PrefixedLogRecord):

    """ A LogRecord subclass splitting incoming messages on newlines and
    converting each to a LogRecord of type `constituent_cls`
    """

    def __init__(self, name, level, fn, lno, msg, *args, constituent_cls=None, **kwargs):
        self.constituents = (
            constituent_cls(name, level, fn, lno, line, *args, *kwargs) for line in msg.split("\n")
        )

        super().__init__(name, level, fn, lno, msg, *args, **kwargs)

class MultilineFormatter(logging.Formatter):

    """ A formatter for MultilineLogRecords, formatting each constituent
    record independently and returning the concatenated result.
    """

    def format(self, record):
        formatted_lines = []

        if not isinstance(record, MultilineLogRecord):
            raise TypeError(
                "MultilineFormatter can only format MultilineLogRecords, "
                f"but received {type(record).__name__}"
            )

        for line_record in record.constituents:
            super_instance = super(MultilineFormatter, self)

            try:
                formatted_lines.append(super_instance.format(line_record))
            except TypeError:

                # When breaking on newlines, message placeholders may not be present in
                # the resulting constituent records, resulting in formatting failures.
                # Fall back to formatting the entire record in such cases.

                formatted_lines = (super_instance.format(record),)
                break

        return "\n".join(formatted_lines)

class ContextfulLogger:

    """ A convenience class providing logging methods matching the level
    names in `logging`. Invocations are forwarded to `logging.log` with the
    appropriate level. A prefix constructed from the positional and keyword
    args to the constructor (modifiable by `amend_context`) is prepended to
    each log message.
    """

    LOGGABLE_LEVELS = [
        "critical",
        "error",
        "warning",
        "info",
        "debug"
    ]

    def __init__(self, *args, **kwargs):
        self.ctx_args = list(args)
        self.ctx_kwargs = kwargs

        self._prefix = self._compile_prefix()

    def amend_context(self, *args, **kwargs):
        self.ctx_args.extend(args)
        self.ctx_kwargs |= kwargs

        self._prefix = self._compile_prefix()

    def _log(self, level, msg, *args, **kwargs):
        logging.log(level, f"{self._prefix} {msg}", *args, **kwargs)

    def _compile_prefix(self):
        args_prefix = ', '.join(self.ctx_args)
        kwargs_prefix = ', '.join(f"{k}={v}" for k, v in self.ctx_kwargs.items())
        separator = ", " if args_prefix and kwargs_prefix else ""

        return f"[{args_prefix}{separator}{kwargs_prefix}]"

    def __getattr__(self, name):
        if name in self.LOGGABLE_LEVELS:
            return partial(self._log, getattr(logging, name.upper()))

        raise AttributeError(f"Cannot forward `{name}` to the `logging` module")

def setup_logging(level_str, extra_level_str, custom_extra_loggers=()):

    """ Set up logging with timestamped and prefixed log records, allowing
    log level differentiation for SQLAlchemy loggers.
    """

    root_logger = logging.getLogger()
    level = getattr(logging, level_str.upper())
    formatter = MultilineFormatter("%(asctime)s %(levelname)7s: %(prefix)s%(message)s")

    extra_loggers = (
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "sqlalchemy.orm",
        "sqlalchemy.engine",
    )

    logging.setLogRecordFactory(make_log_record)

    if not root_logger.handlers:
        logging.basicConfig()

    root_logger.setLevel(level)
    root_logger.handlers[0].setFormatter(formatter)

    if extra_level_str:
        extra_level = getattr(logging, extra_level_str.upper())

        for logger in extra_loggers + custom_extra_loggers:
            logging.getLogger(logger).setLevel(extra_level)

def make_log_record(name, level, fn, lno, msg, args, exc_info, func=None, sinfo=None, **kwargs):

    """ LogRecord factory. Note that path is currently passed as None.
    Implement path name extraction when desired.
    """

    return MultilineLogRecord(
        name, level, None, lno, msg, args, exc_info, func, sinfo, constituent_cls=PrefixedLogRecord
    )

def log_requests(app, make_log_string=None):

    """ Call with an application instance to register an `after_request`
    handler logging all requests.
    """

    if make_log_string is None:
        make_log_string = make_request_log_string

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

def make_request_log_string(request, response):
    return (
        f"Completed {request.method} {request.path} for {request.remote_addr} "
        f"with {response.status}"
    )

def get_logger_level(name=None):
    return logging.getLogger(name).level
