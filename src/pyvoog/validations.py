from functools import wraps

from sqlalchemy import select, Column

from pyvoog.db import get_plain_session
from pyvoog.exceptions import ValidationError

def requires_column(ctor):

    """ Decorator to enforce validator application to SQLAlchemy Columns
    exclusively.
    """

    @wraps(ctor)
    def wrapped(self, column, *args, **kwargs):
        if not isinstance(column, Column):
            raise TypeError(f"The {type(self).__name__} validator may only be applied to a Column")

        return ctor(self, column, *args, **kwargs)

    return wrapped

class Uniqueness:

    """ Enforce a uniqueness constraint on a column. Test if a database
    record with the given value exists, fail if this is the case. A scope
    may optionally be passed as a list of column names.

    This validator requires an `sqlalchemy.Column` as the validatable.
    """

    @requires_column
    def __init__(self, column, scope=[]):
        self.column = column
        self.scope = scope

    def run(self, obj):
        value = getattr(obj, self.column.name)
        id_column = type(obj).__table__.c['id']
        scope_dict = {col_name: getattr(obj, col_name) for col_name in self.scope}
        query = select(True).select_from(obj.__class__) \
            .filter_by(**scope_dict).where(self.column == value, id_column != obj.id)
        row = get_plain_session().execute(query).first()

        if row is not None:
            raise ValidationError(["Is not unique."])

class Inclusion:

    """ Check that a value is included in the given list, fail
    otherwise.
    """

    def __init__(self, attr, belongs_to=[]):
        self.attr = attr
        self.belongs_to = belongs_to

    def run(self, obj):
        value = getattr(obj, self.attr.name)

        if value not in self.belongs_to:
            raise ValidationError(["Does not belong to the set of allowed values."])

class Schema:

    """ Validate a value against a Marshmallow schema. """

    def __init__(self, attr, schema, required=False):
        self.attr = attr
        self.schema = schema
        self.required = required

    def run(self, obj):
        value = getattr(obj, self.attr.name)

        if not value and self.required:
            raise ValidationError("Must be present.")
        elif errors := self.schema().validate(value):
            raise ValidationError(errors)

class Custom:

    """ Delegate validation to a method on the model. """

    def __init__(self, attr, validator_name):
        self.validator_name = validator_name

    def run(self, obj):
        getattr(obj, self.validator_name)()
