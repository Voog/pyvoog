

""" A Flask subclass setting up request logging and responding to HTTP
errors with a JSON payload.
"""

from functools import reduce

import flask as fl
import werkzeug.http

from pyvoog.controller import get_response_tuple
from pyvoog.logging import log_requests
from pyvoog.util import AllowException

class Application(fl.Flask):
    def __init__(self, name):
        super().__init__(name)

        with self.app_context():
            app = fl.current_app

            log_requests(app)

            app._register_error_handlers()

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
