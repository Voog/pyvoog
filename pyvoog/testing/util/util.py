from flask.ctx import AppContext

def setup_app_ctx(app):

    """ Manually set up and push an application context. The caller is
    responsible for tearing down the created context via
    `teardown_app_ctx`.
    """

    app_ctx = AppContext(app)
    app_ctx.push()

    return app_ctx

def teardown_app_ctx(app_ctx):
    app_ctx.pop()
