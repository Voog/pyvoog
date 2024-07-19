from functools import wraps

from werkzeug.exceptions import MethodNotAllowed

from pyvoog.controller import Controller, \
    api_endpoint as make_api_endpoint_decorator, \
    scoped_endpoint, single_object_endpoint, mutating_endpoint
from pyvoog.db import get_session

class ApiBaseController(Controller):

    """ A base controller class for JSON API resources.

    On your controller class, the following class fields are supported for
    configuration:

    - index_order_field - The default field to use for sorting index
      endpoint responses, `id` by default.
    - jwt_secret - base64-encoded JWT secret.
    - allowed_actions - a list of allowed actions on this controller.
    """

    DEFAULT_INDEX_ORDER_FIELD = "id"

    def _api_endpoint(fn):

        """ As we need to query `jwt_secret` from self, defer API endpoint
        decorator construction until the first request - this is in turn wrapped
        in our higher-order `_api_endpoint` decorator.

        Also, check whether the endpoint is enabled here and fail with HTTP/405
        otherwise.
        """

        decorated_fn = None

        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            nonlocal decorated_fn

            self._raise_on_disallowed_action(fn)

            if decorated_fn is None:
                decorated_fn = make_api_endpoint_decorator(jwt_secret=self.jwt_secret)(fn)

            return decorated_fn(self, *args, **kwargs)

        return wrapped

    @_api_endpoint
    @scoped_endpoint
    def index(self, query):
        return (
            self._paginate(query, order_by=self._index_order_field, descending=True),
            200,
        )

    @_api_endpoint
    @single_object_endpoint
    def get(self, obj):
        return obj

    @_api_endpoint
    def create(self, *args, **kwargs):
        session, obj = self._create_object(*args, **kwargs)

        session.commit()
        return obj

    @_api_endpoint
    def update(self, *args, **kwargs):
        session, obj = self._update_object(*args, **kwargs)

        session.commit()
        return obj

    @_api_endpoint
    @single_object_endpoint
    def delete(self, obj):
        session = get_session()

        session.delete(obj)
        session.commit()

        return (None, 204)

    @property
    def _index_order_field(self):
        return getattr(self, "index_order_field", self.DEFAULT_INDEX_ORDER_FIELD)

    @mutating_endpoint
    def _create_object(self, payload):
        attrs = self._permit_attributes(self.schema, payload)
        obj = self.model()
        session = get_session()

        for k, v in attrs.items():
            setattr(obj, k, v)

        if getattr(self, "_run_after_model_population", None):
            self._run_after_model_population(obj, payload, action='create')

        session.add(obj)

        return (session, obj)

    @mutating_endpoint
    @single_object_endpoint
    def _update_object(self, obj, payload):
        attrs = self._permit_attributes(self.schema, payload)
        session = get_session()

        for k, v in attrs.items():
            setattr(obj, k, v)

        if getattr(self, "_run_after_model_population", None):
            self._run_after_model_population(obj, payload, action='update')

        session.add(obj)

        return (session, obj)

    def _raise_on_disallowed_action(self, action):
        allowed_actions = getattr(self, "allowed_actions", None)

        if (allowed_actions is not None) and (action.__name__ not in self.allowed_actions):
            raise MethodNotAllowed()
