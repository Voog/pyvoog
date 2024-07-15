from deepmerge import merge_or_raise
from sqlalchemy import Column

from pyvoog.exceptions import ValidationError
from pyvoog.validations import Custom

class Validatable:

    """ A mixin class providing the `validate` method for installing
    validations on a class and the `is_valid` method for running these.

    A validator is a class:

    - whose constructor conforms to the signature (self, field, ...) where
      `field` is either a `ValidatingColumn` or another Validatable, and
    - which provides a `run` method with the signature (self, obj) where
      `obj` is an instance of an SQLAlchemy model. The method is invoked to
      check the installed constraint against a concrete object. If the
      validation fails, a `ValidationError` must be raised with a string,
      list of error messages, or a dict.

    Note that some validators only accept a subclass of `sqlalchemy.Column`
    as a validatable; in this case, instantiating the validator fails with a
    generic Validatable.

    As a convenience, a string may be passed as the validator. This is a
    shortcut to using the Custom validator; the string is passed as
    `validator_name` to Custom on instantiation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._validations = []

    def validate(self, Validation, **kwargs):
        if type(Validation) is str:
            kwargs = dict(validator_name=Validation)
            Validation = Custom

        self._validations.append(Validation(self, **kwargs))
        return self

    def is_valid(self, obj):

        """ Run all validations on an object, merge the payloads of any
        ValidationErrors and raise these as a combined ValidationError.
        """

        messages = None

        for validation in self._validations:
            try:
                validation.run(obj)
            except ValidationError as e:
                messages = merge_or_raise.merge(messages, e.messages) if messages else e.messages

        if messages:
            raise ValidationError(messages)

class ValidatingColumn(Validatable, Column):

    """ A convenience class mixing in Validatable with Column. """

    inherit_cache = True
