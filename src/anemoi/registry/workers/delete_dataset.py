# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from anemoi.registry.entry.dataset import DatasetCatalogueEntry

from . import Worker

LOG = logging.getLogger(__name__)


class DeleteDatasetWorker(Worker):
    """Worker to delete a dataset from a platform."""

    name = "delete-dataset"

    def __init__(
        self,
        platform,
        filter_tasks={},
        **kwargs,
    ):
        super().__init__(**kwargs)

        if not platform:
            raise ValueError("No destination platform specified")

        self.platform = platform
        self.filter_tasks.update(filter_tasks)

        # TODO: location and platform should be made consistent in the catalogue
        self.filter_tasks["location"] = self.platform

    def worker_process_task(self, task):
        platform, dataset = self.parse_task(task)
        entry = DatasetCatalogueEntry(key=dataset)
        assert platform == self.platform, (platform, self.platform)

        if self.dry_run:
            LOG.warning(
                f"Would delete {entry.record['locations'][platform]['path']} from '{platform}' but this is only a dry run."
            )
            return

        entry.delete_location(platform)

    @classmethod
    def parse_task(cls, task):
        assert task.record["action"] == "delete-dataset", task.record["action"]

        # TODO: location and platform should be made consistent in the catalogue
        platform, dataset = super().parse_task(task, "location", "dataset")

        if "/" in platform:
            raise ValueError(f"platform {platform} must not contain '/', this is a platform name")
        if "." in platform:
            raise ValueError(f"platform {platform} must not contain '.', this is a platform name")

        if "." in dataset:
            raise ValueError(f"The dataset {dataset} must not contain a '.', this is the name of the dataset.")

        return platform, dataset
