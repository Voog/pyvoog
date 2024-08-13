import re

def normalize_path(path_prefix: str) -> str:

    """ Normalize a path, collapsing any slashes within the path and
    removing any slashes at the beginning and end of the path.
    """

    return re.sub(r"^/*|/+", "/", re.sub(r"/+$", "", path_prefix or ""))
