# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging
import os
import tempfile
from getpass import getuser

import yaml
from anemoi.utils.s3 import delete
from anemoi.utils.s3 import download
from anemoi.utils.s3 import upload

from anemoi.registry.rest import RestItemList

from .. import config
from . import CatalogueEntry
from .weights import WeightCatalogueEntry

COLLECTION = "experiments"

LOG = logging.getLogger(__name__)


class ExperimentCatalogueEntryList(RestItemList):
    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield ExperimentCatalogueEntry(key=v["expver"])


class ExperimentCatalogueEntry(CatalogueEntry):
    collection = COLLECTION
    main_key = "expver"

    def create_from_new_key(self, key):
        assert self.key_exists(key) is False, f"{self.collection} with key={key} already exists"
        metadata = dict(expver=key, user=getuser())
        self.key = key
        self.record = dict(expver=key, metadata=metadata, runs={})

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

    def set_run_status(self, run_number, status):
        self.rest_item.patch([{"op": "add", "path": f"/runs/{run_number}/status", "value": status}])

    def create_new_run(self, **kwargs):
        runs = self.record.get("runs", {})
        numbers = [int(k) for k in runs.keys()]
        new = max(numbers) + 1 if numbers else 1
        self._ensure_run_exists(new, **kwargs)
        return new

    def _ensure_run_exists(self, run_number, **kwargs):
        e = self.__class__(key=self.key)

        if "runs" not in e.record:
            # for backwards compatibility, create '/runs' if it does not exist
            e.rest_item.patch([{"op": "add", "path": "/runs", "value": {}}])
            e.record["runs"] = {}

        # add run_number if it does not exist
        if str(run_number) not in self.record.get("runs", {}):
            e.rest_item.patch(
                [
                    {"op": "test", "path": "/runs", "value": e.record["runs"]},
                    {"op": "add", "path": f"/runs/{run_number}", "value": dict(archives={}, **kwargs)},
                ]
            )
            e.record["runs"] = {str(run_number): dict(archives={}, **kwargs)}
        self.record = e.record

    def set_archive(self, path, platform, run_number, overwrite=True, extras={}):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find archive to upload at {path}")

        if run_number is None:
            raise ValueError("run_number must be set")
        run_number = str(run_number)

        if platform is None:
            raise ValueError("platform must be set")

        if isinstance(extras, list):
            extras = {v.split("=")[0]: v.split("=")[1] for v in extras}

        base = os.path.basename(path)
        ext = base.split(os.extsep, 1)[-1]  # everything after the first dot, to support multiple ext like tar.gz
        target = config()["artefacts_uri_base"] + f"/{self.key}/runs/{run_number}/{platform}.{ext}"
        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=overwrite)

        dic = dict(url=target, path=path, updated=datetime.datetime.utcnow().isoformat(), **extras)

        self._ensure_run_exists(run_number)

        self.rest_item.patch([{"op": "add", "path": f"/runs/{run_number}/archives/{platform}", "value": dic}])

    def remove_archive(self, platform, run_number):
        if platform is None:
            raise ValueError("platform must be set")

        run_numbers = self._parse_run_number(run_number)

        for run_number in run_numbers:
            LOG.info(f"Removing archive for run {run_number} and platform {platform}")
            if run_number not in self.record["runs"]:
                LOG.info(f"Archive: skipping run {run_number} because it does not exist")
                continue
            run_record = self.record["runs"][run_number]

            if platform not in run_record.get("archives", {}):
                LOG.info(f"Archive: skipping {platform} for run {run_number} because it does not exist")
                continue

            url = run_record["archives"][platform]["url"]
            delete(url)
            self.rest_item.patch([{"op": "remove", "path": f"/runs/{run_number}/archives/{platform}"}])

    def _list_run_numbers(self):
        return [int(k) for k in self.record.get("runs", {}).keys()]

    def _parse_run_number(self, run_number):
        assert isinstance(run_number, (str, int)), "run_number must be a string or an integer"
        run_number = str(run_number)

        if run_number.lower() == "all":
            return [str(i) for i in self._list_run_numbers()]

        if run_number == "latest":
            run_number = str(max(self._list_run_numbers()))
            LOG.info(f"Using latest run number {run_number}")

        if run_number not in self.record["runs"]:
            raise ValueError(f"Run number {run_number} not found")

        return [run_number]

    def archive_moved(self, old, new, run_number, overwrite=None):
        run_numbers = self._parse_run_number(run_number)

        with tempfile.TemporaryDirectory() as tmpdir:
            print(tmpdir)
            for run_number in run_numbers:
                tmp_path = os.path.join(tmpdir, str(run_number))
                self.get_archive(tmp_path, platform=old, run_number=run_number)
                if not os.path.exists(tmp_path):
                    LOG.info(f"Skipping {old} -> {new} for run {run_number} because it does not exist")
                    continue
                self.set_archive(tmp_path, platform=new, run_number=run_number, overwrite=overwrite)
                self.remove_archive(old, run_number)

    def _get_run_record(self, run_number):
        print(self.record.get("runs", {}), run_number, type(run_number))
        print(self.record.get("runs", {}).get(run_number, {}))
        return self.record.get("runs", {}).get(run_number, {})

    def get_archive(self, path, *, platform, run_number):
        if os.path.exists(path):
            raise FileExistsError(f"Path {path} already exists")

        with tempfile.TemporaryDirectory() as tmpdir:
            run_numbers = self._parse_run_number(run_number)
            for run_number in run_numbers:
                run_record = self._get_run_record(run_number)

                if platform not in run_record.get("archives", {}):
                    LOG.info(f"Archive: skipping {platform} for run {run_number} because it does not exist")
                    continue

                tmp_path = os.path.join(tmpdir, str(run_number))

                url = run_record["archives"][platform]["url"]
                LOG.info(f"Downloading {url} to {tmp_path}.")
                download(url, tmp_path)
                with open(path, "ba+") as f:
                    with open(tmp_path, "br") as tmp:
                        f.write(tmp.read())

    def delete_artefacts(self):
        self.delete_all_plots()
        # self.delete_weights()
        # self.delete_archives()

    def delete_all_plots(self):
        plots = self.record.get("plots", [])
        for plot in plots:
            url = plot["url"]
            LOG.info(f"Deleting {url}")
            if not url.startswith("s3://"):
                LOG.warning(f"Skipping deletion of {url} because it is not an s3 url")
                continue
            if f"/{self.key}/" not in url:
                LOG.warning(f"Skipping deletion of {url} because it does not belong to this experiment")
                continue
            delete(url)
        self.rest_item.patch(
            [
                {"op": "test", "path": "/plots", "value": plots},
                {"op": "add", "path": "/plots", "value": []},
            ]
        )

    def _add_one_plot(self, path, **kwargs):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find plot to upload at {path}")

        target = config()["plots_uri_pattern"]
        basename = os.path.basename(path)
        target = target.format(expver=self.key, basename=basename, filename=basename)

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=True)

        dic = dict(url=target, name=basename, path=path)
        self.rest_item.patch([{"op": "add", "path": "/plots/-", "value": dic}])

    def set_key_json(self, key, file, run_number):
        with open(file, "r") as f:
            value = yaml.safe_load(f)
        return self.set_key(key, value, run_number)

    def set_key(self, key, value, run_number):
        if run_number is None:
            self.rest_item.patch([{"op": "add", "path": f"/{key}", "value": value}])
        else:
            self._ensure_run_exists(run_number)
            self.rest_item.patch([{"op": "add", "path": f"/runs/{run_number}/{key}", "value": value}])

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
