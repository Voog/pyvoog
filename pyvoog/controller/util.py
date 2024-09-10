import functools
import json
import logging
import re

from datetime import datetime
from urllib.parse import urlparse

import flask as fl
import jwt as pyjwt
import werkzeug.http

from marshmallow import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import NoResultFound
from sqlalchemy import select
from werkzeug.exceptions import BadRequest, MethodNotAllowed

from requests.exceptions import (
    RequestException,
    ConnectionError,
    Timeout,
    TooManyRedirects,
)

from pyvoog.db import get_session

from pyvoog.exceptions import (
    AuthenticationError,
    ExternalError,
    ExternalAuthenticationError,
    ValidationError,
)

from pyvoog.signals import jwt_decoded
from pyvoog.util import AllowException

class _ModelEncoder(json.JSONEncoder):

    """ A JSONEncoder subclass with model instance encoding support. """

    def default(self, obj):
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        elif isinstance(obj, datetime):
            return self.zulu_isoformat(obj)

        return json.JSONEncoder.default(self, obj)

    @staticmethod
    def zulu_isoformat(d):
        if d.tzinfo:
            return re.sub(r"\+00:00$", "Z", d.isoformat())

        return d.isoformat()

""" ORM-specific controller decorators """

def scoped_endpoint(fn):

    """ A decorator providing the `query` parameter: an SQLAlchemy statement
    with the default scope applied. Also applies `api_endpoint`.
    """

    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        scope = self.model.default_scope()
        query = select(self.model).filter_by(**scope)

        return fn(self, *args, query=query, **kwargs)

    return wrapped

def single_object_endpoint(fn):

    """ A decorator enhancing `scoped_endpoint` and providing the `obj`
    parameter: an object of `self.model`, looked up by the effective default
    scope and incoming ID.
    """

    @functools.wraps(fn)
    def look_up_object(fn):
        def wrapped(self, *args, id, query, **kwargs):
            obj = get_session().execute(query.filter_by(id=id)).scalar_one()
            return fn(self, *args, obj=obj, **kwargs)

        return wrapped

    return functools.update_wrapper(scoped_endpoint(look_up_object(fn)), fn)

""" Generic API facilities """

def api_endpoint(*dec_args, jwt_secret=None, **dec_kwargs):

    """ A high-level API endpoint decorator factory combining
    `json_endpoint`, `emit_http_codes` and `authenticate`. Arguments are
    passed to the `authenticate` decorator factory.

    If `jwt_secret` is not passed in, it is expected to be an attribute on
    the controller.

    In addition, HTTP/405 is raised if the `allowed_actions` itearble
    attribute is present on the controller and does not contain the
    action servicing the request.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapped(self, *args, **kwargs):
            nonlocal dec_kwargs
            nonlocal jwt_secret

            _raise_on_disallowed_action(controller=self, action=fn)

            if jwt_secret is None:
                jwt_secret = self.jwt_secret

            decorated = json_endpoint(
                emit_http_codes(authenticate(*dec_args, jwt_secret=jwt_secret, **dec_kwargs)(fn))
            )

            return decorated(self, *args, **kwargs)

        return wrapped

    return decorator

def json_endpoint(fn):

    """ Decorator for JSONifying API endpoints. By default the result is
    encoded and returned with the 200 status code. A Response object is
    passed through. If a tuple is returned from the wrapped routine:

    - if its length is one, the element indicates a HTTP status code and the
      payload becomes the matching status string
    - if its length is >1, the first element is the payload, the second is
      the HTTP status code and the optional third element is a dict of extra
      headers.
      """

    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        res = fn(self, *args, **kwargs)
        res_is_tuple = type(res) is tuple
        headers = {"Content-Type": "application/json"}
        payload = res
        code = 200

        if type(res) is fl.Response:
            return res
        elif res_is_tuple and len(res) == 1:
            code = res[0]
            payload = werkzeug.http.HTTP_STATUS_CODES[code]
        elif res_is_tuple:
            payload = res[0]
            code = res[1]

            with AllowException(IndexError):
                if res[2] is not None:
                    headers |= res[2]

        return (json.dumps(payload, cls=_ModelEncoder), code, headers)

    return wrapped

def emit_http_codes(fn):

    """ Turn errors into HTTP/4xx responses:

    - BadRequest — HTTP/400
    - AuthenticationError — HTTP/401
    - None return value or a NoResultFound exception — HTTP/404
    - ValidationError (pyvoog or vanilla Marshmallow) — HTTP/422 with a
      payload describing the errors in `errors`.
    - NotImplementedError — HTTP/501.

    See also `handle_upstream_errors` for a complementary decorator.
    """

    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        try:
            res = fn(self, *args, **kwargs)
        except AuthenticationError as e:
            res = get_response_tuple(401, str(e))
        except NoResultFound:
            res = get_response_tuple(404)
        except BadRequest:
            res = get_response_tuple(400)
        except ValidationError as e:
            res = (dict(errors=e.errors), 422)
        except MarshmallowValidationError as e:
            res = (dict(errors=e.normalized_messages()), 422)
        except NotImplementedError:
            res = get_response_tuple(501)

        return get_response_tuple(404) if res is None else res

    return wrapped

def authenticate(jwt_secret):

    """ The returned decorator raises AuthenticationError on authentication
    failure and emits the `jwt_decoded` signal with the decoded JWT payload
    on success. The `exp` claim is currently required unconditionally on the
    token and stale tokens are rejected.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapped(self, *args, **kwargs):
            jwt = _get_jwt_from_request()

            try:
                payload = pyjwt.decode(
                    jwt, jwt_secret, algorithms="HS256", options=dict(require=["exp"])
                )
            except Exception as e:
                logging.warn(f"Authentication failure for token \"{jwt}\": {e}")
                raise AuthenticationError("Not Authenticated")

            jwt_decoded.send(fl.current_app, payload=payload)
            return fn(self, *args, **kwargs)

        return wrapped

    return decorator

def mutating_endpoint(fn):

    """ A decorator providing the `payload` parameter containing the
    deserialized incoming JSON.
    """

    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        return fn(self, *args, payload=fl.request.get_json(), **kwargs)

    return wrapped

def handle_upstream_errors(fn):

    """ Decorator to turn ExternalAuthenticationErrors into HTTP/401
    responses, all other ExternalErrors into HTTP/502 responses and selected
    Requests exceptions into detailed HTTP/5xx responses.

    See also `emit_http_codes` for a complementary decorator.
    """

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ExternalError as e:
            extra_args = dict(external_message=e.external_message) if e.external_message else {}
            code = 401 if isinstance(e, ExternalAuthenticationError) else 502

            return get_response_tuple(code, e.message, **extra_args)
        except RequestException as e:
            url = e.request.url
            host = urlparse(url).hostname

            if isinstance(e, Timeout):
                code = 504
                message = f"Timed out connecting to {host}"
            elif isinstance(e, ConnectionError):
                code = 500
                message = f"Failed connecting to {host}"
            elif isinstance(e, TooManyRedirects):
                code = 502
                message = f"The request to {url} resulted in too many redirects"
            else:
                raise e

            return get_response_tuple(code, message, details=str(e))

    return wrapped

def get_response_tuple(code, /, message=None, **kwargs):

    """ Utility routine to generate a standard error response payload and
    return it as a pair along with the HTTP error code.
    """

    payload = {
        "message": message or werkzeug.http.HTTP_STATUS_CODES[code],
        **kwargs
    }

    return (payload, code)

def _get_jwt_from_request():
    if not (jwt := fl.request.args.get("token")):
        try:
            jwt = re.split(r"Bearer\s+", fl.request.headers.get("Authorization", ""))[1]
        except Exception:
            jwt = None

    return jwt

def _raise_on_disallowed_action(controller, action):
    allowed_actions = getattr(controller, "allowed_actions", None)

    if (allowed_actions is not None) and (action.__name__ not in controller.allowed_actions):
        raise MethodNotAllowed()
