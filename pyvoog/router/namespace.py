
from attrs import define, field

@define
class Namespace:

    """ Namespace encapsulates one or more Resources with a common path
    prefix.
    """

    path_prefix: str
    resources: list

    def __init__(self, path_prefix, *args):
        self.__attrs_init__(path_prefix=path_prefix, resources=args)
