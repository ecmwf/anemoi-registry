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
            yield TrainingCatalogueEntry(key=v["name"])


class TrainingCatalogueEntry(CatalogueEntry):
    """Catalogue entry for a training."""

    collection = COLLECTION
    main_key = "name"

    @classmethod
    def load_from_path(cls, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".json"), f"{path} must be a json file"

        config = load_any_dict_format(path)

        return cls(
            config["name"],
            dict(uuid=config["uuid"], metadata=config),
            path=path,
        )

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

    @classmethod
    def search_requests(cls, **kwargs):
        """Get the request for the entry."""
        requests = super().search_requests(**kwargs)
        request = dict(name=kwargs["NAME_OR_PATH"])
        requests.append(request)
        return requests
