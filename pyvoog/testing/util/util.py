from contextlib import contextmanager
from datetime import datetime

from flask.ctx import AppContext

from pyvoog.testing.signals import app_ctx_pushed

class TestBreakpoint(Exception):

    """ A utility class useful for early exit from a complex system under
    test. Can be used with an `assertRaises` assertion to verify that a
    point in code was reached or for other purposes where it is not
    desireable to execute an entire code path.
    """

def setup_app_ctx(app):

    """ Manually set up and push an application context. The caller is
    responsible for tearing down the created context via
    `teardown_app_ctx`.

    This should be the single gateway used for setting up a Flask test app
    context, as we call all receivers listening to the `app_ctx_pushed`
    signal here.
    """

    app_ctx = AppContext(app)
    app_ctx.push()

    app_ctx_pushed.send(None, app_ctx=app_ctx)

    return app_ctx

def teardown_app_ctx(app_ctx):
    app_ctx.pop()

@contextmanager
def app_context(app):

    """ A context manager wrapping `setup_app_ctx` and
    `teardown_app_ctx`.
    """

    try:
        app_ctx = setup_app_ctx(app)
        yield app_ctx
    finally:
        teardown_app_ctx(app_ctx)

@contextmanager
def stopwatch():

    """ A context manager for measuring elapsed time. Yields a function
    returning a time delta since entering the context.
    """

    started_at = datetime.now()

    def measure():
        return datetime.now() - started_at

    yield measure
