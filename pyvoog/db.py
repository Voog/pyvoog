import logging

from collections import namedtuple
from contextlib import contextmanager
from itertools import chain

import flask as fl

from sqlalchemy import create_engine, engine, event
from sqlalchemy.orm import Session

from pyvoog.exceptions import NotInitializedError

_PerRequestSession = namedtuple('_PerRequestSession', ['value'])

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
    The teardown listener must be registered separately at app
    initialization, as this is no longer allowed once a request is in
    progress.
    """

    if key not in fl.g:
        logging.debug(f"Setting up per-request session '{key}'")

        if not isinstance(_engine, engine.Engine):
            raise NotInitializedError("Database engine has not been set up.")

        setattr(fl.g, key, _PerRequestSession(cls(_engine)))

    return fl.g.get(key).value

def get_plain_session():

    """ As `get_session`, but yield a vanilla Session instance. """

    return get_session(key="plain_session", cls=Session)

def teardown_sessions(exc):
    session_keys = list(filter(lambda k: isinstance(fl.g.get(k), _PerRequestSession), fl.g))

    for key in session_keys:
        logging.debug(f"Tearing down per-request session '{key}'")

        session = fl.g.pop(key).value
        session.close()

@contextmanager
def temporary_session(cls=ValidatingSession):
    session = cls(_engine)

    try:
        yield session
    finally:
        session.close()
