# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging
import os

import yaml
from anemoi.datasets import open_dataset
from anemoi.utils.humanize import when

from anemoi.registry import config
from anemoi.registry.rest import RestItemList

from . import CatalogueEntry

LOG = logging.getLogger(__name__)

COLLECTION = "datasets"


class DatasetCatalogueEntryList(RestItemList):
    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield DatasetCatalogueEntry(key=v["name"])


class DatasetCatalogueEntry(CatalogueEntry):
    collection = COLLECTION
    main_key = "name"

    def set_status(self, status):
        self.rest_item.patch([{"op": "add", "path": "/status", "value": status}])

    def build_location_path(self, platform, uri_pattern=None):
        if uri_pattern is None:
            assert platform == config()["datasets_platform"]
            uri_pattern = config()["datasets_uri_pattern"]
            LOG.debug(f"Using uri pattern from config: {uri_pattern}")
        else:
            LOG.debug(f"Using uri pattern: {uri_pattern}")
        return uri_pattern.format(name=self.key)

    def add_location(self, platform, path):
        LOG.debug(f"Adding location to {platform}: {path}")
        self.rest_item.patch([{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}])
        return path

    def remove_location(self, platform, *, delete):
        if delete:
            self.delete(platform)
        self.rest_item.patch([{"op": "remove", "path": f"/locations/{platform}"}])

    def delete(self, platform):
        if not config().get("allow_delete"):
            raise ValueError("Delete not allowed by configuration")

        path = self.record.get("locations", {}).get(platform, {}).get("path")
        if path is None:
            LOG.warning(f"Nothing to delete for {self.key} on platform {platform}")
            return
        if path.startswith("s3://"):
            from anemoi.utils.s3 import delete

            return delete(path + "/")
        else:
            LOG.warning(f"Location is not an s3 path: {path}. Delete not implemented.")

    def upload(self, source, target, platform="unknown", resume=True):
        LOG.info(f"Uploading from {source} to {target} ")
        assert target.startswith("s3://"), target

        source_path = os.path.abspath(source)
        kwargs = dict(
            action="transfer-dataset",
            source="cli",
            source_path=source_path,
            destination=platform,
            target_path=target,
            dataset=self.key,
        )
        LOG.info(f"Task: {kwargs}")

        from anemoi.registry.tasks import TaskCatalogueEntry
        from anemoi.registry.tasks import TaskCatalogueEntryList

        def find_or_create_task(**kwargs):
            lst = TaskCatalogueEntryList(**kwargs)

            if not lst:
                LOG.info("No runnning transfer found, starting one.")
                uuid = TaskCatalogueEntryList().add_new_task(**kwargs)
                task = TaskCatalogueEntry(key=uuid)
                return task

            lst = TaskCatalogueEntryList(**kwargs)
            task = lst[0]
            updated = datetime.datetime.fromisoformat(task.record["updated"])
            if resume:
                LOG.info(f"Resuming from previous transfer (last update {when(updated)})")
            else:
                raise ValueError(f"Transfer already in progress (last update {when(updated)})")
            return task

        task = find_or_create_task(**kwargs)
        self.transfer(task, source_path, target, resume=True, threads=2)

    def transfer(self, task, source_path, target, resume, threads):
        from anemoi.utils.s3 import upload

        from anemoi.registry.workers.transfer_dataset import Progress

        progress = Progress(task, frequency=10)
        LOG.info(f"Upload('{source_path}','{target}', resume=True, threads=2)")
        task.set_status("running")
        try:
            upload(source_path, target, resume=resume, threads=threads, progress=progress)
        except:
            task.set_status("stopped")
            raise
        task.unregister()

    def set_recipe(self, file):
        if not os.path.exists(file):
            raise FileNotFoundError(f"Recipe file not found: {file}")
        if not file.endswith(".yaml"):
            LOG.warning("Recipe file extension is not .yaml")
        with open(file) as f:
            recipe = yaml.safe_load(f)
        self.rest_item.patch([{"op": "add", "path": "/recipe", "value": recipe}])

    def load_from_path(self, path):
        import zarr

        if not path.startswith("/") and not path.startswith("s3://"):
            LOG.warning(f"Dataset path is not absolute: {path}")
        if not os.path.exists(path) and not path.startswith("s3://"):
            LOG.warning(f"Dataset path does not exist: {path}")
        if not path.endswith(".zarr") or path.endswith(".zip"):
            LOG.warning("Dataset path extension is neither .zarr nor .zip")

        name, _ = os.path.splitext(os.path.basename(path))

        z = zarr.open(path)
        ds = open_dataset(path)

        metadata = z.attrs.asdict()

        assert "statistics" not in metadata
        metadata["statistics"] = {k: v.tolist() for k, v in ds.statistics.items()}

        assert "shape" not in metadata
        metadata["shape"] = z.data.shape

        assert "dtype" not in metadata
        metadata["dtype"] = str(ds.dtype)

        assert "chunks" not in metadata
        metadata["chunks"] = ds.chunks

        self.key = name
        self.record = dict(name=name, metadata=metadata)
