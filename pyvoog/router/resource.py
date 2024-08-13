from attrs import define, field

@define
class Resource:

    """ A Resource represents a collection of related objects accessible via
    the API, essentially mapping to a controller.

    `name` is used for determining the controller module, the controller
    class name and the path prefix - these could become configurable
    independently in the future.
    """

    name: str
    endpoints: list = None
    include_default_endpoints: bool = False
