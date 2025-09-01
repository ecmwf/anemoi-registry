# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

# ruff: noqa: E402

import importlib
import logging
import os
from functools import cached_property

from anemoi.utils.config import DotDict
from anemoi.utils.config import load_any_dict_format
from anemoi.utils.config import load_config

from anemoi.registry.rest import Rest

LOG = logging.getLogger(__name__)


# TODO : move this function to anemoi.utils.config
def package_config(module_name, missing_ok=False):
    """Load the config.yaml file from the package directory, if it exists."""
    module = importlib.import_module(module_name)
    path = os.path.join(os.path.dirname(module.__file__), "config.yaml")
    if not os.path.exists(path):
        if missing_ok:
            return {}
        else:
            raise FileNotFoundError(f"Config file not found: {path}")

    return DotDict(load_any_dict_format(path))


class SingletonConfig:
    def __init__(self):
        self._cache = None
        self.package_config = package_config("anemoi.registry")

    @cached_property
    def url(self):
        env_var = os.environ.get("ANEMOI_CATALOGUE")

        if env_var == "TEST":
            url = self.package_config["registry"]["test-catalogue"]
            LOG.warning("Using default catalogue URL for testing: %s", url)
            return url

        if env_var is not None:
            LOG.warning("Using catalogue URL from environment variable ANEMOI_CATALOGUE: %s", env_var)
            return env_var

        url_from_user = self._url_from_user_config()
        if url_from_user is not None:
            LOG.warning(f"Overriding default catalogue URL with {url_from_user} from user config.")
            return url_from_user

        return self.package_config["registry"]["catalogue"]

    @cached_property
    def _token(self):
        if os.environ.get("ANEMOI_CATALOGUE_TOKEN") is not None:
            LOG.warning("Using catalogue token from environment variable ANEMOI_CATALOGUE_TOKEN.")
            token = os.environ["ANEMOI_CATALOGUE_TOKEN"]
        else:
            token = load_config(secrets=["api_token"]).get("registry", {}).get("api_token")

        if token is None:
            raise ValueError(
                "No token found. Please add it to your config file or set the ANEMOI_CATALOGUE_TOKEN environment variable."
            )
        return token

    def _url_from_user_config(self):
        return load_config(secrets=["api_token"]).get("registry", {}).get("catalogue")

    def _config_from_server(self):
        if not self.url:
            return {}

        return Rest(token=self._token).get_url(self.url + "/settings")

    def __call__(self, with_secrets=True):
        if self._cache:
            return self._cache

        # from this anemoi-registry package
        conf = self.package_config["registry"]

        # overwritten by server config
        config_from_server = self._config_from_server()
        if "registry" not in config_from_server:
            raise ValueError(
                "No 'registry' section found in the server configuration. "
                + "Please check your server settings or contact the administrator."
                + str(config_from_server)
            )
        for k, v in config_from_server["registry"].items():
            if k not in conf:
                conf[k] = v
            elif isinstance(conf[k], dict) and isinstance(v, dict):
                conf[k].update(v)

        # partly overwritten by config from user
        user_config = load_config(secrets=["api_token"])["registry"]
        for k, v in user_config.items():
            if k in ["api_token"]:  # use token
                conf[k] = v
                continue
            if k in ["allow_delete", "allow_edit_entries"]:  # use these flags, to be removed
                conf[k] = v
                LOG.warning(
                    f"Overriding default {k} with {v} from user config, these flags will disapppear in the future."
                )
                continue
            if v != conf.get(k):  # ignore other keys
                LOG.warning(
                    (
                        f"Ignoring user config for {k}: {v} != {conf.get(k)}."
                        " Please delete this entry from your config file."
                    )
                )
        conf.pop("catalogue")
        conf.pop("test-catalogue")

        if "api_token" not in conf and self._token:
            conf["api_token"] = self._token

        self._cache = conf

        if not with_secrets:
            conf = DotDict({k: v if k != "api_token" else "***" for k, v in conf.items()})
        return conf


CONF = SingletonConfig()


def publish_dataset(*args, **kwargs):
    return Dataset.publish(*args, **kwargs)


from .entry.dataset import DatasetCatalogueEntry as Dataset
from .entry.dataset import DatasetCatalogueEntryList as DatasetsList
from .entry.experiment import ExperimentCatalogueEntry as Experiment
from .entry.experiment import ExperimentCatalogueEntryList as ExperimentsList
from .entry.weights import WeightCatalogueEntry as Weights
from .entry.weights import WeightsCatalogueEntryList as WeightsList
from .tasks import TaskCatalogueEntry as Task
from .tasks import TaskCatalogueEntryList as TasksList

try:
    # NOTE: the `_version.py` file must not be present in the git repository
    #   as it is generated by setuptools at install time
    from ._version import __version__  # type: ignore
except ImportError:  # pragma: no cover
    # Local copy or not installed with setuptools
    __version__ = "999"


__all__ = [
    "Weights",
    "WeightsList",
    "Experiment",
    "ExperimentsList",
    "Dataset",
    "DatasetsList",
    "Task",
    "TasksList",
]
