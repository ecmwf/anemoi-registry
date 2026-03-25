# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""anemoi-registry v2 CLI and Python API."""

import logging

LOG = logging.getLogger(__name__)


def config(*args, **kwargs):
    from .configuration import CONF

    return CONF(*args, **kwargs)


from .entry import CatalogueEntryNotFound
from .entry.dataset import DatasetCatalogueEntry as Dataset
from .entry.dataset import DatasetCatalogueEntryList as DatasetsList
from .entry.experiment import ExperimentCatalogueEntry as Experiment
from .entry.experiment import ExperimentCatalogueEntryList as ExperimentsList
from .entry.replica import ReplicaCatalogueEntry as Replica
from .entry.replica import ReplicaCatalogueEntryList as ReplicasList
from .entry.site import SiteCatalogueEntry as Site
from .entry.site import SiteCatalogueEntryList as SitesList
from .entry.weights import WeightCatalogueEntry as Weights
from .entry.weights import WeightsCatalogueEntryList as WeightsList
from .tasks import TaskCatalogueEntry as Task
from .tasks import TaskCatalogueEntryList as TasksList


__all__ = [
    "CatalogueEntryNotFound",
    "Dataset",
    "DatasetsList",
    "Experiment",
    "ExperimentsList",
    "Replica",
    "ReplicasList",
    "Site",
    "SitesList",
    "Task",
    "TasksList",
    "Weights",
    "WeightsList",
    "config",
]
