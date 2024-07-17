
""" Exports a `GunicornBaseApplication` subclass taking a list of command-
line options for configuration.
"""

from gunicorn.app.base import BaseApplication as GunicornBaseApplication
from gunicorn.config import Config as GunicornConfig

class Server(GunicornBaseApplication):
    def __init__(self, app, argv):
        self.application = app
        self.argv = argv

        super().__init__()

    def load_config(self):
        parser = GunicornConfig(prog="(gunicorn options)").parser()
        args = parser.parse_args(self.argv)

        for k, v in vars(args).items():
            if v is not None and k != "args":
                self.cfg.set(k, v)

    def load(self):
        return self.application
