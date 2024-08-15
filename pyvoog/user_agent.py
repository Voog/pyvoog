import requests

class UserAgent:

    """ A thin wrapper around Requests automatically adding a set of headers
    to the request. A User-Agent may be added as a shortcut.
    """

    def __init__(self, headers={}, user_agent=None):
        if user_agent:
            headers = headers | {"User-Agent": user_agent}

        self.headers = headers

    def __getattr__(self, name):
        def make_request(*args, headers={}, **kwargs):
            method = getattr(requests, name)
            headers = (headers or {}) | self.headers

            return method(*args, headers=headers, **kwargs)

        return make_request
