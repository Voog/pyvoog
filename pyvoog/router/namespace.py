
from attrs import define, field

from .util import normalize_path

@define
class Namespace:

    """ Namespace encapsulates one or more Resources with a common path
    prefix. Path prefixes are normalized.
    """

    path_prefix = field(converter=normalize_path)
    resources = field(factory=list)

    def __init__(self, path_prefix, *args):
        self.__attrs_init__(path_prefix=path_prefix, resources=args)
