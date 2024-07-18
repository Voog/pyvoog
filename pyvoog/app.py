

""" A Flask subclass setting up request logging and responding to HTTP
errors with a JSON payload.
"""

import flask as fl
import werkzeug.http

from pyvoog.db import teardown_sessions
from pyvoog.controller import get_response_tuple
from pyvoog.logging import log_requests
from pyvoog.util import AllowException

class Application(fl.Flask):
    def __init__(self, name=None):
        super().__init__(name or self.__class__.__name__)

        with self.app_context():
            app = fl.current_app

            log_requests(app)
            app._register_error_handlers()
            app._register_teardown_funcs()

            if getattr(self, "__app_post_init__", None):
                self.__app_post_init__()

    def _register_error_handlers(self):

        """ Register error handlers for all valid 4xx and 5xx HTTP status codes
        to return JSON.
        """

        def get_handler(code):
            return lambda _: fl.make_response(
                *get_response_tuple(code),
                {"Content-Type": "application/json"}
            )

        for code, _ in werkzeug.http.HTTP_STATUS_CODES.items():
            if code >= 400:
                with AllowException(KeyError, ValueError):
                    self.register_error_handler(code, get_handler(code))

    def _register_teardown_funcs(self):
        self.teardown_appcontext(teardown_sessions)
