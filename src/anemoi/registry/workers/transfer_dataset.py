# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging
import os
from copy import deepcopy

from anemoi.registry.entry.dataset import DatasetCatalogueEntry

from . import Worker

LOG = logging.getLogger(__name__)


class Progress:
    latest = None

    def __init__(self, task, frequency=60):
        self.task = task
        self.frequency = frequency
        self.first_progress = None
        self.first_transfer_progress = None
        self.previous_progress = None

    def __call__(self, number_of_files, total_size, total_transferred, transfering, **kwargs):
        now = datetime.datetime.utcnow()

        if self.latest is not None and (now - self.latest).seconds < self.frequency:
            # already updated recently
            return
        self.latest = now

        timestamp = now.isoformat()

        progress = dict(
            number_of_files=number_of_files,
            total_size=total_size,
            total_transferred=total_transferred,
            transfering=transfering,
            timestamp=timestamp,
            percentage=100 * total_transferred / total_size if total_size and transfering else 0,
            **kwargs,
        )

        if self.first_progress is None:
            self.first_progress = progress
        if self.first_transfer_progress is None and transfering:
            self.first_transfer_progress = progress

        p = deepcopy(progress)
        p["first_progress"] = self.first_progress
        p["first_transfer_progress"] = self.first_transfer_progress
        p["previous_progress"] = self.previous_progress
        self.task.set_progress(p)

        self.previous_progress = progress


class TransferDatasetWorker(Worker):
    name = "transfer-dataset"

    def __init__(
        self,
        destination,
        target_dir=".",
        published_target_dir=None,
        auto_register=True,
        threads=1,
        filter_tasks={},
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.destination = destination
        self.target_dir = target_dir
        self.published_target_dir = published_target_dir
        self.threads = threads
        self.auto_register = auto_register

        if self.published_target_dir is None:
            self.published_target_dir = self.target_dir

        self.filter_tasks.update(filter_tasks)
        self.filter_tasks["destination"] = self.destination

        if not self.destination:
            raise ValueError("No destination platform specified")

        if not os.path.exists(self.target_dir) and not self.target_dir.startswith("s3://"):
            raise ValueError(f"Target directory {self.target_dir} must already exist")

    def worker_process_task(self, task):
        destination, source, dataset = self.parse_task(task)
        entry = DatasetCatalogueEntry(key=dataset)

        LOG.info(f"Transferring {dataset} from '{source}' to '{destination}'")

        def get_source_path():
            e = entry.record
            if "locations" not in e:
                raise ValueError(f"Dataset {dataset} has no locations")
            locations = e["locations"]

            if source not in locations:
                raise ValueError(
                    f"Dataset {dataset} is not available at {source}. Available locations: {list(locations.keys())}"
                )

            if "path" not in locations[source]:
                raise ValueError(f"Dataset {dataset} has no path at {source}")

            path = locations[source]["path"]

            return path

        source_path = get_source_path()
        basename = os.path.basename(source_path)
        target_path = os.path.join(self.target_dir, basename)
        if os.path.exists(target_path):
            LOG.error(f"Target path {target_path} already exists, skipping.")
            return

        from anemoi.utils.s3 import download
        from anemoi.utils.s3 import upload

        LOG.info(f"Source path: {source_path}")
        LOG.info(f"Target path: {target_path}")

        if source_path.startswith("s3://"):
            source_path = source_path + "/" if not source_path.endswith("/") else source_path

        if self.dry_run:
            LOG.warning(f"Would tranfer {source_path} to {target_path} but this is only a dry run.")
            return

        progress = Progress(task, frequency=10)

        if target_path.startswith("s3://"):
            # upload to S3 uses function upload()
            LOG.info(f"Upload('{source_path}','{target_path}', resume=True, threads={self.threads})")
            upload(source_path, target_path, resume=True, threads=self.threads, progress=progress)
        else:
            # download to local uses function download() and a temporary path
            target_tmp_path = os.path.join(self.target_dir + "-downloading", basename)
            os.makedirs(os.path.dirname(target_tmp_path), exist_ok=True)
            download(source_path, target_tmp_path, resume=True, threads=self.threads, progress=progress)
            os.rename(target_tmp_path, target_path)

        if self.auto_register:
            published_target_path = os.path.join(self.published_target_dir, basename)
            entry.add_location(platform=destination, path=published_target_path)

    @classmethod
    def parse_task(cls, task):
        assert task.record["action"] == "transfer-dataset", task.record["action"]

        destination, source, dataset = super().parse_task(task, "destination", "source", "dataset")

        if "/" in destination:
            raise ValueError(f"Destination {destination} must not contain '/', this is a platform name")
        if "." in destination:
            raise ValueError(f"Destination {destination} must not contain '.', this is a platform name")

        if "/" in source:
            raise ValueError(f"Source {source} must not contain '/', this is a platform name")
        if "." in source:
            raise ValueError(f"Source {source} must not contain '.', this is a platform name")

        if "." in dataset:
            raise ValueError(f"The dataset {dataset} must not contain a '.', this is the name of the dataset.")

        return destination, source, dataset
