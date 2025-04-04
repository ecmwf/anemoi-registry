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
    main_key = "uuid"

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".json"), f"{path} must be a json file"

        config = load_any_dict_format(path)

        # metadata = config.pop("metadata")
        # metadata["config"] = config
        # metadata["config_training"] = config
        # training_id = metadata["training_uid"]
        self.key = config["uuid"]
        self.record = dict(uuid=config["uuid"], metadata=config["metadata"])

    def register(self, overwrite=False, ignore_existing=True, **kwargs):
        assert self.record, "record must be set"
        record = self.record.copy()
        record.pop("uuid")
        return self._rest_item.put(record, **kwargs)
