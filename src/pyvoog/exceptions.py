
import marshmallow

class AuthenticationError(Exception):
    pass

class NotInitializedError(Exception):
    pass

class ValidationError(marshmallow.ValidationError):
    @property
    def errors(self):
        return self.messages
