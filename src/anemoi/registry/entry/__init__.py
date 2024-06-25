# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import json
import logging
import os

import requests
import yaml
from anemoi.datasets import open_dataset
from anemoi.utils.checkpoints import load_metadata as load_checkpoint_metadata
from anemoi.utils.s3 import upload

from anemoi.registry import config
from anemoi.registry.rest import AlreadyExists
from anemoi.registry.rest import Rest

# from anemoi.registry.rest import DryRunRest as Rest


def json_dump_pretty(obj, max_line_length=120):
    """Custom JSON dump function that keeps dicts and lists on one line if they are short enough.

    Parameters
    ----------
    obj
        The object to be dumped as JSON.
    max_line_length
        Maximum allowed line length for pretty-printing.

    Returns
    -------
    unknown
        JSON string.
    """

    def _format_json(obj, indent_level=0):
        """Helper function to format JSON objects with custom pretty-print rules.

        Parameters
        ----------
        obj
            The object to format.
        indent_level
            Current indentation level.

        Returns
        -------
        unknown
            Formatted JSON string.
        """
        indent = " " * 4 * indent_level
        if isinstance(obj, dict):
            items = []
            for key, value in obj.items():
                items.append(f'"{key}": {_format_json(value, indent_level + 1)}')
            line = "{" + ", ".join(items) + "}"
            if len(line) <= max_line_length:
                return line
            else:
                return "{\n" + ",\n".join([f"{indent}    {item}" for item in items]) + "\n" + indent + "}"
        elif isinstance(obj, list):
            items = [_format_json(item, indent_level + 1) for item in obj]
            line = "[" + ", ".join(items) + "]"
            if len(line) <= max_line_length:
                return line
            else:
                return "[\n" + ",\n".join([f"{indent}    {item}" for item in items]) + "\n" + indent + "]"
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        else:
            return json.dumps(obj)

    return _format_json(obj)


LOG = logging.getLogger(__name__)


class CatalogueEntryNotFound(Exception):
    pass


class CatalogueEntry:
    record = None
    path = None
    key = None
    rest = Rest()

    def __init__(self, key=None, path=None):
        assert key is not None or path is not None, "key or path must be provided"

        if path is not None:
            assert key is None
            self.load_from_path(path)
            assert self.record is not None
        else:
            assert key is not None
            self.load_from_key(key)
            assert self.record is not None

        assert self.key is not None, "key must be provided"

    def as_json(self):
        return json_dump_pretty(self.record)

    @classmethod
    def key_exists(cls, key):
        try:
            cls._get_record_from_catalogue(key)
            return True
        except CatalogueEntryNotFound:
            return False

    def load_from_key(self, key):
        self.key = key
        self.record = self._get_record_from_catalogue(key)

    @classmethod
    def _get_record_from_catalogue(cls, key):
        try:
            return cls.rest.get(f"{cls.collection_api}/{key}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise CatalogueEntryNotFound(f"Could not find any {cls.collection_api} with key={key}")
            raise

    @property
    def main_key(self):
        raise NotImplementedError("Subclasses must implement this property")

    def register(self, ignore_existing=True, overwrite=False):
        try:
            return self.rest.post(self.collection_api, self.record)
        except AlreadyExists:
            if ignore_existing:
                return
            if overwrite is True:
                LOG.warning(f"{self.key} already exists. Deleting existing one to overwrite it.")
                return self.replace()
            raise

    def replace(self):
        return self.rest.put(f"{self.collection_api}/{self.key}", self.record)

    def patch(self, payload):
        return self.rest.patch(f"{self.collection_api}/{self.key}", payload)

    def unregister(self, force=False):
        if not self.rest.config.get("allow_delete"):
            raise ValueError("Unregister not allowed")
        return self.rest.delete(f"{self.collection_api}/{self.key}?force=True")

    def __repr__(self):
        return json.dumps(self.record, indent=2)


class ExperimentCatalogueEntry(CatalogueEntry):
    collection_api = "experiments"
    main_key = "expver"

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".yaml"), f"{path} must be a yaml file"

        with open(path, "r") as file:
            config = yaml.safe_load(file)

        metadata = config.pop("metadata")
        metadata["config"] = config
        expver = metadata["expver"]

        self.key = expver
        self.record = dict(expver=expver, metadata=metadata)

    def add_plots(self, path, target=None):
        """target is a pattern: s3://bucket/{expver}/{basename}"""

        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find plot at {path}")

        if target is None:
            target = config()["plots_uri_pattern"]
        basename = os.path.basename(path)
        target = target.format(expver=self.key, basename=basename, filename=basename)

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=True)

        dic = dict(url=target, name=basename, path=path)
        patch = [{"op": "add", "path": "/plots/-", "value": dic}]
        self.patch(patch)

    def add_weights(self, path):
        """target is a pattern: s3://bucket/{uuid}"""

        weights = WeightCatalogueEntry(path=path)
        if not WeightCatalogueEntry.key_exists(weights.key):
            weights.register(ignore_existing=False, overwrite=False)
            weights.upload(path, overwrite=False)
        else:
            other = WeightCatalogueEntry(key=weights.key)
            if other.record["metadata"]["timestamp"] == weights.record["metadata"]["timestamp"]:
                LOG.info(
                    f"Not updating weights with key={weights.key}, because it already exists and has the same timestamp"
                )
            else:
                raise ValueError(f"Conflicting weights with key={weights.key}")

        dic = dict(uuid=weights.key, path=path)
        patch = [{"op": "add", "path": "/checkpoints/-", "value": dic}]
        self.patch(patch)


class WeightCatalogueEntry(CatalogueEntry):
    collection_api = "weights"
    main_key = "uuid"

    def add_location(self, platform, path):
        patch = [{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}]
        self.patch(patch)

    def default_location(self, **kwargs):
        uri = config()["weights_uri_pattern"]
        uri = uri.format(uuid=self.key, **kwargs)
        return uri

    def default_platform(self):
        return config()["weights_platform"]

    def upload(self, path, target=None, overwrite=False):
        if target is None:
            target = self.default_location()

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=overwrite, resume=not overwrite)
        return target

    def register(self, overwrite=False):
        assert self.path is not None, "path must be provided"

        platform = self.default_platform()
        target = self.upload(self.path)
        self.register(overwrite=overwrite)
        self.add_location(platform=platform, path=target)

    def load_from_path(self, path):
        self.path = path
        assert os.path.exists(path), f"{path} does not exist"

        metadata = load_checkpoint_metadata(path)
        assert "path" not in metadata
        metadata["path"] = os.path.abspath(path)

        metadata["size"] = os.path.getsize(path)

        uuid = metadata.get("uuid")
        if uuid is None:
            uuid = metadata["run_id"]
            LOG.warning(f"Could not find 'uuid' in {path}, using 'run_id' instead: {uuid}")

        self.key = uuid
        self.record = dict(uuid=uuid, metadata=metadata)


class DatasetCatalogueEntry(CatalogueEntry):
    collection_api = "datasets"
    main_key = "name"

    def set_status(self, status):
        patch = [{"op": "add", "path": "/status", "value": status}]
        self.patch(patch)

    def add_location(self, platform, path):
        patch = [{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}]
        self.patch(patch)

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
