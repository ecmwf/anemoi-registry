# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os

from ._version import __version__ as __version__

LOG = logging.getLogger(__name__)


def config():
    from anemoi.utils.config import load_config

    default_config = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = load_config(secrets=["api_token"], defaults=default_config)
    return config.get("registry")


from .entry.dataset import DatasetCatalogueEntry as Dataset
from .entry.dataset import DatasetCatalogueEntryList as DatasetsList
from .entry.experiment import ExperimentCatalogueEntry as Experiment
from .entry.experiment import ExperimentCatalogueEntryList as ExperimentsList
from .entry.weights import WeightCatalogueEntry as Weights
from .entry.weights import WeightsCatalogueEntryList as WeightsList
from .tasks import TaskCatalogueEntry as Task
from .tasks import TaskCatalogueEntryList as TasksList

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
