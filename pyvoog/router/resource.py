
from pyvoog.util import make_repr

class Resource:

    """ A Resource represents a collection of related objects accessible via
    the API, essentially mapping to a controller.
    """

    def __init__(self, name, endpoints=None, include_default_endpoints=False):
        self.name = name
        self.endpoints = endpoints
        self.include_default_endpoints = include_default_endpoints

    def __repr__(self):
        return make_repr(self)
