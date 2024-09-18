# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import json
import logging
from functools import cached_property

from anemoi.utils.humanize import json_pretty_dump

from anemoi.registry import config
from anemoi.registry.rest import AlreadyExists
from anemoi.registry.rest import RestItem
from anemoi.registry.rest import RestItemList

# from anemoi.registry.rest import DryRunRest as Rest


LOG = logging.getLogger(__name__)


class CatalogueEntryNotFound(Exception):
    pass


class CatalogueEntry:
    record = None
    path = None
    key = None
    collection = None

    @property
    def url(self):
        return f"{config()['web_url']}/{self.collection}/{self.key}"

    def __init__(self, key=None, path=None, must_exist=True):
        assert key is not None or path is not None, "key or path must be provided"
        assert key is None or path is None, "key and path are mutually exclusive"

        if path is not None:
            self.load_from_path(path)

        if key is not None:
            if self.key_exists(key):
                # found in catalogue so load it
                self.load_from_key(key)
            else:
                # not found in catalogue, so create a new one
                if must_exist:
                    raise CatalogueEntryNotFound(f"Could not find any {self.collection} with key={key}")
                else:
                    self.create_from_new_key(key)

        assert self.record is not None
        assert self.key is not None, "key must be provided"

        self.rest_item = RestItem(self.collection, self.key)
        self.rest_collection = RestItemList(self.collection)

    def as_json(self):
        return json_pretty_dump(self.record)

    @classmethod
    def key_exists(cls, key):
        return RestItem(cls.collection, key).exists()

    def exists(self):
        return self.rest_item.exists()

    def load_from_key(self, key):
        rest_item = RestItem(self.collection, key)
        if rest_item.exists():
            self.key = key
            self.record = rest_item.get()
        else:
            raise CatalogueEntryNotFound(f"Could not find any {self.collection} with key={key}")

    @property
    def main_key(self):
        raise NotImplementedError("Subclasses must implement this property")

    def register(self, overwrite=False, ignore_existing=True):
        assert self.record, "record must be set"
        try:
            return self.rest_collection.post(self.record)
        except AlreadyExists:
            if overwrite is True:
                LOG.warning(f"{self.key} already exists. Deleting existing one to overwrite it.")
                return self.rest_item.put(self.record)
            if ignore_existing:
                LOG.info(f"{self.key} already exists. Ok.")
                return
            raise

    def json(self):
        print(self.as_json())

    def patch(self, data):
        return self.rest_item.patch(data)

    def unregister(self):
        return self.rest_item.delete()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.rest_collection}, {self.key})"
