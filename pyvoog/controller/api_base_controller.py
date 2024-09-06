from functools import wraps

from pyvoog.controller import Controller, \
    api_endpoint, scoped_endpoint, single_object_endpoint, mutating_endpoint
from pyvoog.db import get_session

class ApiBaseController(Controller):

    """ A base controller class for JSON API resources.

    On your controller class, the following class fields are supported for
    configuration:

    - allowed_actions - a list of allowed actions on this controller.
    - index_order_field - The default field to use for sorting index
      endpoint responses, `id` by default.
    - jwt_secret - base64-encoded JWT secret.
    - model - the backing model of this controller.
    - schema - the Marshmallow schema of acceptable payloads.
    """

    DEFAULT_INDEX_ORDER_FIELD = "id"

    @api_endpoint()
    @scoped_endpoint
    def index(self, query):
        return (
            self.paginate(query, order_by=self._index_order_field, descending=True),
            200,
        )

    @api_endpoint()
    @single_object_endpoint
    def get(self, obj):
        return obj

    @api_endpoint()
    def create(self, *args, **kwargs):
        session, obj = self._create_object(*args, **kwargs)

        session.commit()
        return obj

    @api_endpoint()
    def update(self, *args, **kwargs):
        session, obj = self._update_object(*args, **kwargs)

        session.commit()
        return obj

    @api_endpoint()
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
        attrs = self.permit_attributes(self.schema, payload)
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
        attrs = self.permit_attributes(self.schema, payload)
        session = get_session()

        for k, v in attrs.items():
            setattr(obj, k, v)

        if getattr(self, "_run_after_model_population", None):
            self._run_after_model_population(obj, payload, action='update')

        session.add(obj)

        return (session, obj)
