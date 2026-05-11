# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..entry.dataset import DatasetCatalogueEntry
from . import Worker

LOG = logging.getLogger(__name__)


class DeleteDatasetWorker(Worker):
    """Worker to delete a dataset from a platform."""

    name = "delete-dataset"

    def __init__(
        self,
        location,
        filter_tasks={},
        **kwargs,
    ):
        super().__init__(**kwargs)

        if not location:
            raise ValueError("No location specified")

        self.location = location
        self.filter_tasks.update(filter_tasks)
        self.filter_tasks["location"] = self.location

    def worker_process_task(self, task):
        location, dataset = self.parse_task(task)
        entry = DatasetCatalogueEntry(key=dataset)
        assert location == self.location, (location, self.location)

        if self.dry_run:
            LOG.warning(
                f"Would delete {entry.record['locations'][location]['path']} from '{location}' but this is only a dry run."
            )
            return

        entry.delete_location(location)

    @classmethod
    def parse_task(cls, task):
        assert task.record["action"] == "delete-dataset", task.record["action"]

        location, dataset = super().parse_task(task, "location", "dataset")

        if "/" in location:
            raise ValueError(f"Location {location} must not contain '/', this is a platform name")
        if "." in location:
            raise ValueError(f"Location {location} must not contain '.', this is a platform name")

        if "." in dataset:
            raise ValueError(f"The dataset {dataset} must not contain a '.', this is the name of the dataset.")

        return location, dataset
