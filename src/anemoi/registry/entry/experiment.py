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
from anemoi.utils.s3 import download
from anemoi.utils.s3 import upload

from .. import config
from . import CatalogueEntry
from .weights import WeightCatalogueEntry

LOG = logging.getLogger(__name__)


class ExperimentCatalogueEntry(CatalogueEntry):
    collection = "experiments"
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
        self.record = dict(expver=expver, metadata=metadata, runs={})

    def add_plots(self, *paths, **kwargs):
        for path in paths:
            self._add_one_plot(path, **kwargs)

    def add_weights(self, *paths, **kwargs):
        for path in paths:
            self._add_one_weights(path, **kwargs)

    def set_archive(self, path, platform, run_number, overwrite, extras):
        if run_number is None:
            raise ValueError("run_number must be set")
        if platform is None:
            raise ValueError("platform must be set")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find archive to upload at {path}")
        extras = {v.split("=")[0]: v.split("=")[1] for v in extras}

        _, ext = os.path.splitext(path)
        target = config()["artefacts_uri_base"] + f"/{self.key}/runs/{run_number}/{platform}{ext}"
        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=overwrite)

        dic = dict(url=target, path=path, updated=datetime.datetime.utcnow().isoformat(), **extras)

        if "runs" not in self.record:
            # for backwards compatibility, create '/runs' if it does not exist
            e = self.__class__(key=self.key)
            if "runs" not in e.record:
                e.rest_item.patch([{"op": "add", "path": "/runs", "value": {}}])
                self.record["runs"] = {}

        if str(run_number) not in self.record["runs"]:
            # add run_number if it does not exist
            self.rest_item.patch(
                [
                    {"op": "add", "path": "/runs", "value": self.record["runs"]},
                    {"op": "add", "path": f"/runs/{run_number}", "value": dict(archives={})},
                ]
            )

        self.rest_item.patch([{"op": "add", "path": f"/runs/{run_number}/archives/{platform}", "value": dic}])

    def get_archive(self, path, run_number, platform):
        if os.path.exists(path):
            raise FileExistsError(f"Path {path} already exists")
        if run_number not in self.record["runs"]:
            raise ValueError(f"Run number {run_number} not found")
        if platform not in self.record["runs"][run_number]["archives"]:
            raise ValueError(f"Platform {platform} not found")
        url = self.record["runs"][run_number]["archives"][platform]["url"]
        print(url)
        download(url, path)

    def _add_one_plot(self, path, **kwargs):
        kind = "plot"
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find {kind} to upload at {path}")

        target = config()[f"{kind}s_uri_pattern"]
        basename = os.path.basename(path)
        target = target.format(expver=self.key, basename=basename, filename=basename)

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=True)

        dic = dict(url=target, name=basename, path=path)
        self.rest_item.patch([{"op": "add", "path": f"/{kind}s/-", "value": dic}])

    def _add_one_weights(self, path, **kwargs):
        weights = WeightCatalogueEntry(path=path)

        if not WeightCatalogueEntry.key_exists(weights.key):
            # weights with this uuid does not exist, register and upload them
            weights.register(ignore_existing=False, overwrite=False)
            weights.upload(path, overwrite=False)

        else:
            # Weights with this uuid already exist
            # Skip if the weights are the same
            # Raise an error if the weights are different
            other = WeightCatalogueEntry(key=weights.key)
            if other.record["metadata"]["timestamp"] == weights.record["metadata"]["timestamp"]:
                LOG.info(
                    f"Not updating weights with key={weights.key}, because it already exists and has the same timestamp"
                )
            else:
                raise ValueError(f"Conflicting weights with key={weights.key}")

        dic = dict(uuid=weights.key, path=path)
        self.rest_item.patch([{"op": "add", "path": "/checkpoints/-", "value": dic}])
