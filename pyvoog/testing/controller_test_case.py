from collections.abc import Mapping
from contextlib import contextmanager
from unittest import TestCase

from pyvoog.db import get_plain_session
from pyvoog.testing.util.controllers import controller_fixture

class ControllerTestCase(TestCase):
    @contextmanager
    def post_response(self, model=None, payload=None):

        """ A context manager making a POST request to `self.ENDPOINT` with the
        given payload, using `self.jwt_secret` and `self.jwt_payload` for
        constructing the authentication token, and yielding the response.

        If the request is successful, `model` is present and the response body
        is a JSON object containing `id`, the persisted object is cleaned up.
        """

        with controller_fixture(
            self.app, jwt_secret=self.jwt_secret, jwt_payload=self.jwt_payload
        ) as ua:
            response = ua.post(self.ENDPOINT, json=payload)

        with self.app.app_context():
            session = get_plain_session()

            try:
                yield response
            finally:
                json = response.json
                id = isinstance(json, Mapping) and json.get("id", None)

                if model and (id is not None) and response.status_code < 400:
                    session.delete(session.get(model, id))
                    session.commit()
