import requests

from attrs import define, field

@define
class UserAgent:

    """ A thin wrapper around Requests automatically adding a set of headers
    to the request. A User-Agent may be added as a shortcut.
    """

    user_agent: str = None
    headers: dict = {}

    def __attrs_post_init__(self):
        if self.user_agent:
            self.headers = self.headers | {"User-Agent": self.user_agent}

    def __getattr__(self, name):
        def make_request(*args, headers={}, **kwargs):
            method = getattr(requests, name)
            headers = self.headers | headers

            return method(*args, headers=headers, **kwargs)

        return make_request
