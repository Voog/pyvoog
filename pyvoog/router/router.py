import importlib
import logging
import re

import flask as fl

from attrs import define
from stringcase import snakecase

from .endpoint import Endpoint
from .namespace import Namespace
from .resource import Resource
from .util import normalize_path

@define
class Router:
    controller_ns: str

    DEFAULT_ENDPOINTS_TEMPLATE = [
        dict(path="{}s", methods=["GET"], action="index"),
        dict(path="{}s", methods=["POST"], action="create"),
        dict(path="{}/<int:id>", methods=["GET"], action="get"),
        dict(path="{}/<int:id>", methods=["PUT"], action="update"),
        dict(path="{}/<int:id>", methods=["DELETE"], action="delete")
    ]

    def route(self, table):

        """ Route requests to controllers based on the incoming iterable routing
        table containing Resources (optionally wrapped in Namespaces), in turn
        containing Endpoints specifying the actions handling matching requests.
        A Resource is not required to contain explicit endpoints — if no
        endpoints are configured, a default set of RESTful endpoints for the
        resource are set up.

        The controller module to import from the namespace specified by
        `controller_ns` is inferred from the path prefix and resource name. The
        module is expected to contain a class with a name constructed by
        titlecasing the resource name and appending "Controller" to it, which is
        instantiated with the app object. The controller must contain a method
        for every action specified in Endpoints for serving the specified
        request.
        """

        for namespace_or_resource in table:
            if isinstance(namespace_or_resource, Namespace):
                resources = namespace_or_resource.resources
                path_prefix = namespace_or_resource.path_prefix
            elif isinstance(namespace_or_resource, Resource):
                resources = (namespace_or_resource,)
                path_prefix = "/"
            else:
                raise TypeError(
                    "Expected a Namespace or Resource in the routing table, "
                    f"but received {namespace_or_resource}"
                )

            for resource in resources:
                self._route_resource(path_prefix, resource)

    def _route_resource(self, path_prefix, resource):
        if not isinstance(resource, Resource):
            raise TypeError(
                f"Expected a Resource in router config, but received {resource}"
            )

        module = self._import_controller(path_prefix=path_prefix, resource=resource)
        controller_cls = getattr(module, resource.ctrlr_class_name)
        controller = controller_cls()
        endpoints = resource.endpoints if resource.endpoints else []

        if not endpoints or resource.include_default_endpoints:
            endpoints += self._populate_default_endpoints(resource.name)

        for endpoint in endpoints:
            if not isinstance(endpoint, Endpoint):
                raise TypeError(
                    f"Expected an Endpoint in Resource config, but received {endpoint}"
                )

            self._route_to_controller(controller, path_prefix, endpoint)

    def _route_to_controller(self, controller, path_prefix, endpoint):

        """ Route paths (path prefix + endpoint path) to controller actions. """

        path = normalize_path(f"{path_prefix}/{endpoint.path}")
        func = getattr(controller, endpoint.action)
        ctrlr_name = type(controller).__name__
        endpoint_name = snakecase(f"{ctrlr_name}_{endpoint.action}")

        logging.info(
            f"Adding route: {path} -> {ctrlr_name}.{endpoint.action} "
            f"({','.join(endpoint.methods)})"
        )

        fl.current_app.add_url_rule(
          path,
          view_func=func,
          endpoint=endpoint_name,
          methods=endpoint.methods
        )

    def _import_controller(self, path_prefix, resource):
        stripped_path_prefix = re.sub(r"^/+", "", path_prefix)
        ns_infix = f".{stripped_path_prefix.replace('/', '.')}." if stripped_path_prefix else "."
        module_name = f"{self.controller_ns}{ns_infix}{resource.ctrlr_module_name}"

        return importlib.import_module(module_name)

    def _populate_default_endpoints(self, name):
        return map(
            lambda kws: Endpoint(**(kws | {"path": kws["path"].format(name)})),
            self.DEFAULT_ENDPOINTS_TEMPLATE
        )
