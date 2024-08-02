from pyvoog.db import get_session

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