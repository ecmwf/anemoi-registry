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

import yaml
from anemoi.utils.config import load_any_dict_format
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
    """Base class for a Anemoi catalogue entry."""

    record = None
    path = None
    key = None
    collection = None

    @property
    def url(self):
        return f"{config()['web_url']}/{self.collection}/{self.key}"

    def load_from_path(self, path):
        raise NotImplementedError("Subclasses must implement this method")

    def __init__(self, key=None, path=None, must_exist=True, params=None):
        assert key is not None or path is not None, "key or path must be provided"
        assert key is None or path is None, "key and path are mutually exclusive"

        if path is not None:
            self.load_from_path(path)

        if key is not None:
            if self.key_exists(key):
                # found in catalogue so load it
                self.load_from_key(key, params=params)
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

    def load_from_key(self, key, params=None):
        rest_item = RestItem(self.collection, key)
        if rest_item.exists():
            self.key = key
            self.record = rest_item.get(params=params)
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
                LOG.warning(f"{self.key} already exists. Overwriting existing one.")
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

    def set_value_from_file(self, key, file):
        value = load_any_dict_format(file)
        self.set_value(key, value)

    def get_value(self, path):
        # Read a value from the record using a path:
        # path is a string with keys separated by dots or slashes.
        # e.g. "metadata.updated" or "metadata/updated"
        # list indices are also supported, e.g. "metadata.tags.0"

        rec = self.record
        for p in self._path_to_list(path):
            if isinstance(rec, list):
                rec = rec[int(p)]
            elif isinstance(rec, dict):
                rec = rec[p]
            else:
                raise KeyError(f"Cannot get value for {path} in {self.record}. {p} is not a key in {rec}")
        return rec

    def _path_to_list(self, path):
        if path.startswith("/"):
            path = path[1:]
            path = ".".join(path.split("/"))
        return path.split(".")

    def set_value(self, path, value, type_=None, increment_update=False):
        return self.patch_value("add", path, value=value, type_=type_, increment_update=increment_update)

    def remove_value(self, key, increment_update=False):
        return self.patch_value("remove", key, increment_update=increment_update)

    def patch_value(self, op, path, value=None, type_=None, from_=None, increment_update=False):

        if not path.startswith("/"):
            path = "/" + path
            path = path.replace(".", "/")

        patch = {"op": op, "path": path}

        if op in ("add", "replace", "test"):

            if type_ is not None:
                # if type provided, cast value to type

                if type_ == "stdin" and value != "-":
                    raise ValueError(f"Invalid value for type {type_}: Expecting '-', got '{value}'")

                value = {
                    "int": int,
                    "float": float,
                    "bool": bool,
                    "stdin": load_any_dict_format,
                    "path": load_any_dict_format,
                    "yaml": yaml.safe_load,
                    "json": json.loads,
                }[type_](value)

            patch["value"] = value

        if from_ is not None:
            patch["from"] = from_

        patches = [patch]
        if increment_update:
            updated = self.record["metadata"].get("updated", 0)
            patches = [{"op": "add", "path": "/metadata/updated", "value": updated + 1}] + patches

        LOG.debug(f"jsonpatch: {patches}")

        self.patch(patches)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.rest_collection}, {self.key})"
