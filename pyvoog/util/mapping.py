import collections
from collections.abc import Mapping, MutableMapping

class VanillaDict(dict):

    """ A helper class for data structures passed into
    mapping_to_namedtuple. VanillaDicts are not converted into named tuples
    and remain dicts.
    """

def mapping_to_namedtuple(mapping, class_name="MappingToNamedtuple"):

    """ Recursively convert a mapping to a namedtuple. """

    nt = collections.namedtuple(class_name, mapping.keys())(**mapping)

    for (k, v) in mapping.items():
        is_mapping = isinstance(v, Mapping) or isinstance(v, MutableMapping)

        if not is_mapping or isinstance(v, VanillaDict):
            continue
        nt = nt._replace(**{k: mapping_to_namedtuple(v, class_name)})

    return nt

def filter_mapping(fn, mapping):

    """ A `filter` counterpart for mapping types, with the same signature
    and parameter semantics (as far as applicable to mappings). Filtering
    applies to values.

    See:

    https://docs.python.org/3/library/functions.html#filter
    """

    if fn is None:
        fn = lambda x: x

    return {k: v for k, v in mapping.items() if fn(v)}
