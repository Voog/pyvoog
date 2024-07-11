import logging

from functools import partial
from itertools import chain, filterfalse

import flask as fl

from sqlalchemy import create_engine, engine, event
from sqlalchemy.orm import Session

from pyvoog.exceptions import NotInitializedError

_engine = None

class ValidatingSession(Session):

    """ A Session automatically attaching a before_flush hook to run
    validations on all models.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event.listen(self, "before_flush", self.__class__.run_validations)

    @staticmethod
    def run_validations(session, flush_context, instances):
        for obj in chain(session.new, session.dirty):
            obj.validate()

def setup_database(db_url, **kwargs):
    global _engine

    _engine = create_engine(db_url, echo=False, future=True, pool_pre_ping=True, **kwargs)

    return _engine

def get_session(key="session", cls=ValidatingSession):

    """ Return a per-request SQLAlchemy Session, creating one if needed.
    There may be several active sessions, differentiated by the given key.
    Register a teardown listener to close the session. Remove any listeners
    for the given key that are already present beforehand.
    """

    app = fl.current_app

    if key not in fl.g:
        logging.debug(f"Setting up per-request session '{key}'")

        if not isinstance(_engine, engine.Engine):
            raise NotInitializedError("Database engine has not been set up.")

        app.teardown_appcontext_funcs = \
            list(filterfalse(_get_teardown_fn_filter(key), app.teardown_appcontext_funcs))

        setattr(fl.g, key, cls(_engine))
        app.teardown_appcontext(partial(_teardown_session, key))

    return fl.g.get(key)

def get_plain_session():

    """ As `get_session`, but yield a vanilla Session instance. """

    return get_session(key="plain_session", cls=Session)

def _teardown_session(key, exc):
    logging.debug(f"Tearing down per-request session '{key}'")

    if session := fl.g.pop(key, None):
        session.close()

def _get_teardown_fn_filter(key):

    """ Return a predicate returning True if the given function is a session
    teardown listener for the given key.
    """

    def is_teardown_fn(fn):
        is_partial = hasattr(fn, "args") and hasattr(fn, "func")
        return is_partial and fn.func.__name__ == "_teardown_session" and fn.args[0] == key

    return is_teardown_fn
