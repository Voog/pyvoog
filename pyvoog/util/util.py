import importlib
import inspect

class AllowException:

    """ Prefer `contextlib.suppress` as a builtin alternative. """

    def __init__(self, *excs):
        self.excs = excs

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type and any(issubclass(exc_type, our_exc_type) for our_exc_type in self.excs)):
            return True
        return False

class Undefined:

    """ A class to convey a null value, distinct from None. """

def make_namespace_importer(module_template, subclass_of, return_class=False):

    """ A function returning factory receiving a code, importing a module
    based on the code, extracting a class from the imported module and
    returning an instance of the class.

    - module_template - A module name format string containing the `code`
      placeholder, filled in by the factory for the resolved module name.
    - subclass_of - A class acting as a filter - the imported module's
      members are scanned and the first found class that is a strict
      subclass of `subclass_of` is used for instantiation.
    - return_class - Instead of instantiating the class, return the
      class itself.

    importlib raises a ModuleNotFoundError if the expected module cannot be
    loaded; an ImportError is raised if the specified subclass is not
    present in the module.
    """

    def cls_filter(m):
        return inspect.isclass(m) \
            and issubclass(m, subclass_of) \
            and m is not subclass_of

    def import_by_code(code, *args, **kwargs):
        module_name = module_template.format(code=code)
        module = importlib.import_module(module_name)

        try:
            cls = inspect.getmembers(module, cls_filter)[0][1]
        except IndexError:
            raise ImportError(f"Cannot find a {subclass_of.__name__} subclass in {module_name}")

        if return_class:
            return cls

        return cls(*args, **kwargs)

    return import_by_code

def make_repr(obj):

    """ Generate an informative repr for `obj`. Consider using attrs, as it
    provides a nice repr as a bonus.
    """

    attrs = ", ".join(f"{k}={v}" for k, v in vars(obj).items())

    return f"<{type(obj).__name__}({attrs})>"
