from contextlib import contextmanager

from flask.ctx import AppContext

from pyvoog.testing.signals import app_ctx_pushed

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