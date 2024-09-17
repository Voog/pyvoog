import marshmallow

from attrs import define, field
from requests import Response

class AuthenticationError(Exception):
    pass

class NotInitializedError(Exception):
    pass

class ValidationError(marshmallow.ValidationError):
    @property
    def errors(self):
        return self.messages

@define(str=True)
class ExternalError(Exception):

    """ An error raised due to an external system returning an error
    condition.
    """

    message: str = None
    external_message: str = None
    response: Response = None

class ExternalAuthenticationError(ExternalError):
    pass
