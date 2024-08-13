
from pyvoog.util import make_repr

class Endpoint:

    """ Endpoint represents a concrete a path spec and supported HTTP verbs
    mapping to a controller action on a Resource.
    """

    def __init__(self, path, action, methods=["GET"]):
        self.path = path
        self.action = action
        self.methods = methods

    def __repr__(self):
        return make_repr(self)
