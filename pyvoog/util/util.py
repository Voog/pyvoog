
import collections

from collections.abc import Mapping, MutableMapping

from jwt import JWT, jwk_from_dict

class AllowException:
    def __init__(self, *excs):
        self.excs = excs

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type and any(issubclass(exc_type, our_exc_type) for our_exc_type in self.excs)):
            return True
        return False

class Undefined:

    """ A class to convey a null value, distinct from None. """


class VanillaDict(dict):

    """ A helper class for data structures passed into
    mapping_to_namedtuple. VanillaDicts are not converted into named tuples
    and remain dicts.
    """

def decode_jwt(jwt, secret, **decode_args):
    jwk = jwk_from_dict({"kty": "oct", "k": secret})
    decode_args = {"do_time_check": True} | decode_args
    message = JWT().decode(jwt, jwk, **decode_args)

    return message

def mapping_to_namedtuple(mapping, class_name):

    """ Recursively convert a mapping to a namedtuple. """

    nt = collections.namedtuple(class_name, mapping.keys())(**mapping)

    for (k, v) in mapping.items():
        is_mapping = isinstance(v, Mapping) or isinstance(v, MutableMapping)

        if not is_mapping or isinstance(v, VanillaDict):
            continue
        nt = nt._replace(**{k: mapping_to_namedtuple(v, class_name)})

    return nt
