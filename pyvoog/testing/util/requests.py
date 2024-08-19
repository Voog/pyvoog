from contextlib import contextmanager
from time import time

import flask as fl
import jwt

from flask.testing import FlaskClient
from werkzeug.test import EnvironBuilder

from .util import app_context

class _AuthenticatedClient(FlaskClient):
    def __init__(
        self, *args, headers={}, jwt_payload=None, jwt_secret=None, set_jwt_exp=True, **kwargs
    ):
        self.headers = headers

        if jwt_payload and jwt_secret:
            if set_jwt_exp:
                jwt_payload = jwt_payload | dict(exp=time() * 1.1)

            token = jwt.encode(jwt_payload, jwt_secret)
            self.headers = self.headers | {"Authorization": f"Bearer {token}"}

        super().__init__(*args, **kwargs)

    def open(self, *args, **kwargs):
        return super().open(*args, headers=self.headers, **kwargs)

@contextmanager
def controller_fixture(app, **client_kwargs):

    """ Yield a context manager setting up a Flask app context and a test
    client for use in controller testing. The context variable is a
    FlaskClient subclass instance intended to make convenient authenticated
    requests. Pass `jwt_secret` and `jwt_payload` to construct a token,
    included with every request. If `set_jwt_exp` is true, a future
    timestamp is appended to the payload. Extra custom HTTP headers may be
    included via `headers`.
    """

    app.test_client_class = _AuthenticatedClient

    with app_context(app):
        yield app.test_client(**client_kwargs)

def build_request(*args, **kwargs):

    """ Forward arguments to EnvironBuilder and return a Flask Request based
    on the constructed env.
    """

    builder = EnvironBuilder(*args, **kwargs)

    return fl.Request(builder.get_environ())
