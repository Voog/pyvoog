from marshmallow import Schema, EXCLUDE, RAISE

def make_schema(**d):

    """ Create a Marshmallow schema instance from the incoming dict. Permit
    unknown keys and exclude these.
    """

    return Schema.from_dict(d)(unknown=EXCLUDE)

def make_strict_schema(**d):

    """ As `make_schema`, but do not allow unknown keys. """

    return Schema.from_dict(d)(unknown=RAISE)