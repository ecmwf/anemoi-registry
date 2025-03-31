# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json
import logging
import os
from getpass import getuser

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
        self.record = dict(training_id=key, metadata=metadata)

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".json"), f"{path} must be a json file"

        with open(path, "r") as file:
            config = json.load(file)

        metadata = config.pop("metadata")
        metadata["config"] = config
        metadata["config_training"] = config
        training_id = metadata["training_uid"]
        self.key = training_id
        self.record = dict(training_id=training_id, metadata=metadata)

    def delete_artefacts(self):
        pass

    def set_key_json(self, key, file):
        with open(file, "r") as f:
            value = json.load(f)
        return self.set_key(key, value)

    def set_key(self, key, value):
        self.patch([{"op": "add", "path": f"/{key}", "value": value}])
