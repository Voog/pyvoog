from attrs import define, field
from stringcase import pascalcase

@define
class Resource:

    """ A Resource represents a collection of related objects accessible via
    the API, essentially mapping to a controller.

    - name - Used for determining the controller module, the controller
      class name and the path prefix for default endpoints.
    - ctrlr_class_name - Explicitly set the name of controller class mapping
      to the Resource.
    - ctrlr_module_name - Explicitly set the suffix of the controller module
      mapping to the Resource. The router's `controller_ns` and any
      encapsulating namespace's path prefix are nevertheless respected.
    """

    name: str = None
    endpoints: list = []
    include_default_endpoints: bool = False
    ctrlr_class_name: str = None
    ctrlr_module_name: str = None

    def __attrs_post_init__(self):
        if not self.name and (
            not self.ctrlr_class_name
            or not self.ctrlr_module_name
            or self.include_default_endpoints
        ):
            raise ValueError(
                "`ctrlr_module_name` and `ctrlr_class_name` are required, and "
                "`include_default_endpoints` must be False if `name` is not provided for a Resource"
            )

        if not self.ctrlr_class_name:
            self.ctrlr_class_name = f"{pascalcase(self.name)}Controller"

        if not self.ctrlr_module_name:
            self.ctrlr_module_name = self.name
