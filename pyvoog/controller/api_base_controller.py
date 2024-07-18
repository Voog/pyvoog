from functools import wraps

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
    - allowed_methods - TODO
    """

    DEFAULT_INDEX_ORDER_FIELD = "id"

    def _api_endpoint(fn):
        decorated_fn = None

        @wraps(fn)
        def wrapped(self, *args, **kwargs):
            nonlocal decorated_fn

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
        obj = self.model() # TODO: implement mutation hooks
        session = get_session()

        for k, v in attrs.items():
            setattr(obj, k, v)

        session.add(obj)

        return (session, obj)

    @mutating_endpoint
    @single_object_endpoint
    def _update_object(self, obj, payload):
        attrs = self._permit_attributes(self.schema, payload)
        session = get_session()

        for k, v in attrs.items():
            setattr(obj, k, v)

        session.add(obj)

        return (session, obj)
