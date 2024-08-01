import os
import os.path
import sys

from functools import reduce

def drop_last_path_components(path, n):

    """ Given a path, normalize it using `abspath`, drop its last `n`
    components and return the result.
    """

    return reduce(lambda acc, _: os.path.split(acc)[0], range(n), os.path.abspath(path))

def set_root_directory(dirname):

    """ Change cwd to `dirname` and append it to `sys.path`. Useful for
    initializing scripts to work in the project's environment. Passes
    through `dirname` for convenience.
    """

    os.chdir(dirname)

    if dirname not in sys.path:
        sys.path.append(dirname)

    return dirname
