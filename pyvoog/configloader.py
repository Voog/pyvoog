
from pyvoog.exceptions import NotInitializedError
from pyvoog.util.mapping import mapping_to_namedtuple

import importlib
import os
import re

class ConfigLoader:

    """ A class for loading the configuration from config.*, according
    to the environment passed in the environment variable `envvar`. The
    default environment is always loaded; the secondary environment
    overwrites the default configuration values.

    If `overwrite_prefix` is specified, all configuration values can be
    overridden using environment variables. The name of the environment
    variable must be the overwrite prefix and configuration key combined,
    uppercased. For instance, if the overwrite prefix is "MY_APP", the
    environment variable "MY_APP_CACHE_BACKEND" will take precedence over
    the `cache_backend` configuration value.
    """

    CONFIG_PKG = "config"

    def __init__(self, envvar=None, env=None, overwrite_prefix=None):
        config = self._load_env("default")
        env_from_env = envvar and os.environ.get(envvar, None)
        effective_env = env_from_env or env

        if effective_env:
            config.update(self._load_env(effective_env))

        self.env = env
        self.config = config
        self.overwrite_prefix = overwrite_prefix

    def load(self):
        global _config

        _config = mapping_to_namedtuple(self._overwrite_from_os_env(self.config), "Config")

        return config

    def _load_env(self, env):
        return importlib.import_module("{}.{}".format(self.CONFIG_PKG, env)).config

    def _overwrite_from_os_env(self, config):
        prefix = self.overwrite_prefix

        if prefix is not None:
            var_name_regex = fr"{prefix}(\w+)$"
            overwrites = {}

            for k, v in os.environ.items():
                if m := re.match(var_name_regex, k):
                    config_key = m[1].lower()
                    overwrites[config_key] = v

            config.update(overwrites)

        return config

class _Config:
    @staticmethod
    def __contains__(key):
        return hasattr(_config, key)

    @staticmethod
    def __getattr__(name):
        if not _config:
            raise NotInitializedError("Configuration has not been initialized")

        return getattr(_config, name)

    @staticmethod
    def __getitem__(key):
        if hasattr(_config, key):
            return getattr(_config, key)

        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

_config = None
config = _Config()
