# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os

import yaml
from anemoi.datasets import open_dataset

from . import CatalogueEntry

LOG = logging.getLogger(__name__)


class DatasetCatalogueEntry(CatalogueEntry):
    collection = "datasets"
    main_key = "name"

    def set_status(self, status):
        self.rest_item.patch([{"op": "add", "path": "/status", "value": status}])

    def add_location(self, path, platform):
        self.rest_item.patch([{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}])

    def remove_location(self, platform):
        self.rest_item.patch([{"op": "remove", "path": f"/locations/{platform}"}])

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
