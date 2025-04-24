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

from anemoi.utils.config import load_any_dict_format

from anemoi.registry.rest import RestItemList

from . import CatalogueEntry
from .weights import TrainingWeightCatalogueEntry

COLLECTION = "trainings"

LOG = logging.getLogger(__name__)


class TrainingCatalogueEntryList(RestItemList):
    """List of TrainingCatalogueEntry objects."""

    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield TrainingCatalogueEntry(key=v["name"])


class TrainingCatalogueEntry(CatalogueEntry):
    """Catalogue entry for a training."""

    collection = COLLECTION
    main_key = "name"

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".json"), f"{path} must be a json file"

        config = load_any_dict_format(path)

        self.key = config["name"]
        self.record = dict(uuid=config["uuid"], metadata=config["metadata"])

    def register(self, overwrite=False, ignore_existing=True, **kwargs):
        assert self.record, "record must be set"
        record = self.record.copy()
        record.pop("uuid")
        return self._rest_item.put(record, **kwargs)

    def set_key_json(self, key, file):
        assert os.path.exists(file), f"{file} does not exist"
        assert file.endswith(".json"), f"{file} must be a json file"

        value = load_any_dict_format(file)
        return self.set_key(key, value)

    def set_key(self, key, value):
        self.patch([{"op": "add", "path": f"/{key}", "value": value}])

    def add_weights(self, *paths, **kwargs):
        for path in paths:
            self._add_one_weights(path, **kwargs)

    def _add_one_weights(self, path, **kwargs):
        training_metadata = {
            "uuid": self.record["uuid"],
            "key": self.key,
        }
        weights = TrainingWeightCatalogueEntry(path=path, training_config=training_metadata)

        if not TrainingWeightCatalogueEntry.key_exists(weights.key):
            # weights with this uuid does not exist, register and upload them
            weights.register(ignore_existing=False, overwrite=False)
            weights.upload(path, overwrite=False)

        else:
            # Weights with this uuid already exist
            # Skip if the weights are the same
            # Raise an error if the weights are different
            other = TrainingWeightCatalogueEntry(key=weights.key)
            if other.record["metadata"]["timestamp"] == weights.record["metadata"]["timestamp"]:
                LOG.info(
                    f"Not updating weights with key={weights.key}, because it already exists and has the same timestamp"
                )
            else:
                raise ValueError(f"Conflicting weights with key={weights.key}")

        dic = dict(uuid=weights.key, path=path)
        self.patch([{"op": "add", "path": "/checkpoints/-", "value": dic}], robust=True)
