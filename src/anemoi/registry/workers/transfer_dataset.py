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

        if not destination:
            raise ValueError("No destination platform specified")

        if not os.path.exists(target_dir):
            raise ValueError(f"Target directory {target_dir} must already exist")

        self.destination = destination
        self.target_dir = target_dir
        self.published_target_dir = published_target_dir or target_dir
        self.threads = threads
        self.filter_tasks.update(filter_tasks)
        self.filter_tasks["destination"] = self.destination
        self.auto_register = auto_register

    def process_task(self, task):
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

        LOG.info(f"Source path: {source_path}")
        LOG.info(f"Target path: {target_path}")

        if source_path.startswith("s3://"):
            source_path = source_path + "/" if not source_path.endswith("/") else source_path

        if target_path.startswith("s3://"):
            LOG.warning("Uploading to S3 is experimental and has not been tested yet.")
            download(source_path, target_path, resume=True, threads=self.threads)
            return
        else:
            target_tmp_path = os.path.join(self.target_dir + "-downloading", basename)
            os.makedirs(os.path.dirname(target_tmp_path), exist_ok=True)
            download(source_path, target_tmp_path, resume=True, threads=self.threads)
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