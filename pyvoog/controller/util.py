import functools
import json
import logging
import re

from datetime import datetime

import flask as fl
import jwt as pyjwt
import werkzeug.http

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from werkzeug.exceptions import BadRequest

from pyvoog.db import get_session
from pyvoog.exceptions import AuthenticationError, ValidationError
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
        def wrapped(self, *args, _id, query, **kwargs):
            obj = get_session().execute(query.filter_by(id=_id)).scalar_one()
            return fn(self, *args, obj=obj, **kwargs)

        return wrapped

    return functools.update_wrapper(scoped_endpoint(look_up_object(fn)), fn)

""" Generic API facilities """

def api_endpoint(*args, **kwargs):

    """ A high-level API endpoint decorator factory combining
    `json_endpoint`, `emit_http_codes` and `authenticate`. Arguments are
    passed to the `authenticate` decorator factory.
    """

    def decorator(fn):
        return functools.update_wrapper(
            json_endpoint(emit_http_codes(authenticate(*args, **kwargs)(fn))),
            fn
        )

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
    - ValidationError — HTTP/422 with a payload describing the errors in
      `errors`.
    - NotImplementedError — HTTP/501.
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
