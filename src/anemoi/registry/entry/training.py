# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os
from getpass import getuser

import json

from anemoi.registry.rest import RestItemList

from . import CatalogueEntry

COLLECTION = "trainings"

LOG = logging.getLogger(__name__)


class TrainingCatalogueEntryList(RestItemList):
    """List of TrainingCatalogueEntry objects."""

    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield TrainingCatalogueEntry(key=v["training-id"])


class TrainingCatalogueEntry(CatalogueEntry):
    """Catalogue entry for a training."""

    collection = COLLECTION
    main_key = "training-id"

    def create_from_new_key(self, key):
        assert self.key_exists(key) is False, f"{self.collection} with key={key} already exists"
        metadata = dict(training_id=key, user=getuser())
        self.key = key
        self.record = dict(training_id=key, metadata=metadata, runs={})

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".json"), f"{path} must be a json file"

        with open(path, "r") as file:
            config = json.load(file)
            
        metadata = config.pop("metadata")
        metadata["config"] = config
        metadata["config_training"] = config
        training_id = metadata["training-uid"]
        
        self.key = training_id
        self.record = dict(training_id=training_id, metadata=metadata, runs={})

    def set_run_status(self, run_number, status):
        self.patch([{"op": "add", "path": f"/runs/{run_number}/status", "value": status}], robust=True)

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
            e.patch([{"op": "add", "path": "/runs", "value": {}}], robust=True)
            e.record["runs"] = {}

        # add run_number if it does not exist
        if str(run_number) not in self.record.get("runs", {}):
            e.patch(
                [
                    {"op": "test", "path": "/runs", "value": e.record["runs"]},
                    {"op": "add", "path": f"/runs/{run_number}", "value": dict(archives={}, **kwargs)},
                ],
                robust=True,
            )
            e.record["runs"] = {str(run_number): dict(archives={}, **kwargs)}
        self.record = e.record

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

    def _get_run_record(self, run_number):
        print(self.record.get("runs", {}), run_number, type(run_number))
        print(self.record.get("runs", {}).get(run_number, {}))
        return self.record.get("runs", {}).get(run_number, {})

    def delete_artefacts(self):
        pass

    def set_key_json(self, key, file, run_number):
        with open(file, "r") as f:
            value = json.load(f)
        return self.set_key(key, value, run_number)

    def set_key(self, key, value, run_number):
        if run_number is None:
            self.patch([{"op": "add", "path": f"/{key}", "value": value}])
        else:
            self._ensure_run_exists(run_number)
            self.patch([{"op": "add", "path": f"/runs/{run_number}/{key}", "value": value}])
