import importlib
import logging
import re

import flask as fl
from stringcase import pascalcase, snakecase

from .resource import Resource
from .endpoint import Endpoint

class Router:
    DEFAULT_ENDPOINTS_TEMPLATE = [
        dict(path="{}s", methods=["GET"], action="index"),
        dict(path="{}s", methods=["POST"], action="create"),
        dict(path="{}/<int:_id>", methods=["GET"], action="get"),
        dict(path="{}/<int:_id>", methods=["PUT"], action="update"),
        dict(path="{}/<int:_id>", methods=["DELETE"], action="delete")
    ]

    def route(self, config):

        """ Route requests to controllers based on the incoming configuration
        dict mapping path prefixes to Resources containing Endpoints. A
        Resource is not required to contain explicit endpoints — if no
        endpoints are configured, a default set of RESTful endpoints for the
        resource are set up.

        The controller module to import from `pyvoog.controllers` is inferred from
        the path prefix and resource name. The module is expected to contain a
        class with a name constructed by titlecasing the resource name and
        appending "Controller" to it, which is instantiated with the app object.
        The controller must contain a method for every action specified in
        Endpoints for serving the specified request.
        """

        for path_prefix, resources in config.items():
            for resource in resources:
                self._route_resource(path_prefix, resource)

    def _route_resource(self, path_prefix, resource):
        if not isinstance(resource, Resource):
            raise TypeError(
                f"Expected a Resource in router config, but received {resource}"
            )

        path_prefix = re.sub(r"/+", "/", re.sub(r"^/+|/+$", "", path_prefix))
        module_name = f"pyvoog.controllers.{path_prefix.replace('/', '.')}.{resource.name}"
        module = importlib.import_module(module_name)
        controller_cls = getattr(module, f"{pascalcase(resource.name)}Controller")
        controller = controller_cls()
        endpoints = resource.endpoints if resource.endpoints else []

        if not endpoints or resource.include_default_endpoints:
            endpoints += self._populate_default_endpoints(resource.name)

        for endpoint in endpoints:
            if not isinstance(endpoint, Endpoint):
                raise TypeError(
                    f"Expected an Endpoint in Resource config, but received {endpoint}"
                )

            self._route_to_controller(controller, f"/{path_prefix}", endpoint)

    def _route_to_controller(self, controller, path_prefix, endpoint):

        """ Route paths (path prefix + endpoint path) to controller actions. """

        path = f"{path_prefix}/{endpoint.path}"
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

    def _populate_default_endpoints(self, name):
        return map(
            lambda kws: Endpoint(**(kws | {"path": kws["path"].format(name)})),
            self.DEFAULT_ENDPOINTS_TEMPLATE
        )
