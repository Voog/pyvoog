import requests

from attrs import define, field

@define
class UserAgent:

    """ A thin wrapper around Requests automatically adding a set of headers
    to the request. A User-Agent may be added as a shortcut. All other
    arguments to `request` (or rather its wrappers) may be set on the
    instance by `default_rq_args`.
    """

    user_agent: str = None
    headers: dict = {}
    default_rq_args: dict = {}

    def __attrs_post_init__(self):
        if self.user_agent:
            self.headers = self.headers | {"User-Agent": self.user_agent}

    def __getattr__(self, name):
        def make_request(*args, headers={}, **kwargs):
            method = getattr(requests, name)
            headers = self.headers | headers
            extra_rq_kwargs = self.default_rq_args | kwargs

            return method(*args, headers=headers, **extra_rq_kwargs)

        return make_request
