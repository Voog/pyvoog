from contextlib import contextmanager

from pyvoog.db import get_session

@contextmanager
def temporary_object(model, persist=False, **kwargs):

    """ Temporarily persist a model instance, making it available within a
    context manager and discarding it after use.
    """

    session = get_session()
    obj = create_object(model, session=session, **kwargs)

    try:
        yield obj
    finally:
        if not persist:
            session.delete(obj)
            session.commit()

def create_object(model, session=None, **kwargs):
    session = session or get_session()
    obj = initialize_object(model, **kwargs)

    session.add(obj)
    session.commit()

    return obj

def initialize_object(model, **kwargs):
    obj = model()

    for k, v in kwargs.items():
        setattr(obj, k, v)

    return obj

def delete_object(obj, session=None):
    session = session or get_session()

    session.delete(obj)
    session.commit()