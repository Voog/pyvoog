from collections.abc import Mapping
from contextlib import contextmanager
from unittest import TestCase

from pyvoog.db import get_plain_session
from pyvoog.testing.util.models import temporary_object
from pyvoog.testing.util.requests import controller_fixture

class ControllerTestCase(TestCase):

    """ A controller test suite base class, providing convenience
    routines for making typical requests. Respects the following
    attributes on the object:

    - ENDPOINT - the default endpoint for making requests.
    - jwt_secret - JWT secret for constructing the access token.
    - jwt_payload - JWT payload for constructing the access token.
    """

    @contextmanager
    def get_response(self, model, model_args, endpoint=None):

        """ A context manager constructing a temporary instance of `model`
        with `model_args`, making a GET request to an endpoint and yielding
        the response.

        `endpoint` may be a string or a callable (in which case the callable is
        invoked with `obj` and its result used as the effective endpoint).
        `self.ENDPOINT` is used as the default callback.
        """

        with self.bound_controller_fixture as ua:
            with temporary_object(model, **model_args) as obj:
                if callable(endpoint):
                    effective_endpoint = endpoint(obj)
                else:
                    effective_endpoint = endpoint or self.ENDPOINT

                yield ua.get(effective_endpoint)

    @contextmanager
    def post_response(self, model=None, payload=None):

        """ A context manager making a POST request to `self.ENDPOINT` and
        yielding the response.

        If the request is successful, `model` is present and the response body
        is a JSON object containing `id`, the persisted object is cleaned up.
        """

        with self.bound_controller_fixture as ua:
            response = ua.post(self.ENDPOINT, json=payload)
            session = get_plain_session()

            try:
                yield response
            finally:
                json = response.json
                id = isinstance(json, Mapping) and json.get("id", None)

                if model and (id is not None) and response.status_code < 400:
                    session.delete(session.get(model, id))
                    session.commit()

    @property
    def bound_controller_fixture(self):

        """ Return a `controller_fixture` context manager bound to the app under
        test and authentication credentials.
        """

        return controller_fixture(
            self.app, jwt_secret=self.jwt_secret, jwt_payload=self.jwt_payload
        )
