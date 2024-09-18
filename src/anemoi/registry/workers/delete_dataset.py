# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os

from anemoi.registry.entry.dataset import DatasetCatalogueEntry

from . import Worker

LOG = logging.getLogger(__name__)


class DeleteDatasetWorker(Worker):
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
        self.filter_tasks["platform"] = self.platform

    def worker_process_task(self, task):
        platform, dataset = self.parse_task(task)
        entry = DatasetCatalogueEntry(key=dataset)
        assert platform == self.platform, (platform, self.platform)

        locations = entry.record.get("locations", {})
        if platform not in locations:
            LOG.warning(f"Dataset {dataset} has no locations on '{platform}'. Ignoring delete request.")
            return
        if self.dry_run:
            LOG.warning(f"Would delete {locations[platform]['path']} from '{platform}' but this is only a dry run.")
            return

        path = locations[platform]["path"]
        LOG.warning(f"Deleting {path} from '{platform}'")

        tmp_path = path + ".deleting"
        i = 0
        while os.path.exists(tmp_path):
            i += 1
            tmp_path = path + ".deleting." + str(i)
        os.rename(path, tmp_path)

        # shutil.rmtree(tmp_path)
        LOG.warning(f"Deleted {path} from '{platform}'")

        entry.remove_location(platform)
        LOG.warning(f"Removed location from catalogue {path} from '{platform}'")

    @classmethod
    def parse_task(cls, task):
        assert task.record["action"] == "delete-dataset", task.record["action"]

        platform, dataset = super().parse_task(task, "platform", "dataset")

        if "/" in platform:
            raise ValueError(f"Platform {platform} must not contain '/', this is a platform name")
        if "." in platform:
            raise ValueError(f"Platform {platform} must not contain '.', this is a platform name")

        if "." in dataset:
            raise ValueError(f"The dataset {dataset} must not contain a '.', this is the name of the dataset.")

        return platform, dataset
