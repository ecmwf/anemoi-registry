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
from anemoi.utils.dates import as_datetime
from anemoi.utils.dates import as_timedelta
from anemoi.utils.humanize import json_pretty_dump

from anemoi.registry import config
from anemoi.registry.rest import AlreadyExists
from anemoi.registry.rest import RestItem
from anemoi.registry.rest import RestItemList

# from anemoi.registry.rest import DryRunRest as Rest


LOG = logging.getLogger(__name__)

VALUES_PARSERS = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "stdin": load_any_dict_format,
    "path": load_any_dict_format,
    "yaml": yaml.safe_load,
    "json": json.loads,
    "datetime": as_datetime,
    "timedelta": as_timedelta,
}


def parse_value(value, type_):
    if type_ is None:
        return value

    if type_ == "stdin" and value != "-":
        raise ValueError(f"Invalid value for type {type_}: Expecting '-', got '{value}'")

    if type_ not in VALUES_PARSERS:
        raise ValueError(f"Invalid type {type_}. Supported types are: {list(VALUES_PARSERS.keys())}")

    return VALUES_PARSERS[type_](value)


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

        self._rest_item = RestItem(self.collection, self.key)
        self.rest_collection = RestItemList(self.collection)

    def as_json(self):
        return json_pretty_dump(self.record)

    @classmethod
    def key_exists(cls, key):
        return RestItem(cls.collection, key).exists()

    def exists(self):
        return self._rest_item.exists()

    def load_from_key(self, key, params=None):
        _rest_item = RestItem(self.collection, key)
        if _rest_item.exists():
            self.key = key
            self.record = _rest_item.get(params=params)
        else:
            raise CatalogueEntryNotFound(f"Could not find any {self.collection} with key={key}")

    @property
    def main_key(self):
        raise NotImplementedError("Subclasses must implement this property")

    def register(self, overwrite=False, ignore_existing=True, **kwargs):
        assert self.record, "record must be set"
        try:
            return self.rest_collection.post(self.record, **kwargs)
        except AlreadyExists:
            if overwrite is True:
                LOG.warning(f"{self.key} already exists. Overwriting existing one.")
                return self._rest_item.put(self.record, **kwargs)
            if ignore_existing:
                LOG.info(f"{self.key} already exists. Ok.")
                return
            raise

    def json(self):
        print(self.as_json())

    def patch(self, data, *args, **kwargs):
        return self._rest_item.patch(data, *args, **kwargs)

    def unregister(self, *args, **kwargs):
        return self._rest_item.delete(*args, **kwargs)

    def unprotected_unregister(self, *args, **kwargs):
        return self._rest_item.unprotected_delete(*args, **kwargs)

    @classmethod
    def resolve_path(cls, path, check=True):
        # Add /metadata/ to the path if it is not there, because the rest of the catalogue record should not be changed.
        # But, if the user configuration allows it, allow to top level paths anyway with
        #  - path starting with '//', containing '/' as separators
        #  - path starting with '...' or '..'

        def raise_if_needed(p):
            if p.startswith("/metadata/"):
                return p
            if check and not config().get("allow_edit_entries"):
                raise ValueError(
                    "Editing entries is not allowed, only metadata can be changed. "
                    "Please set value to true in your config file if you know what you are doing."
                )
            return p

        if path.startswith("/"):
            # This is a top level path
            # separator is now '/' and path is absolute
            return raise_if_needed(path)

        if path.startswith("."):
            path = path.replace(".", "/")
            # This is a top level path
            # separator is now '/' and path is absolute
            return raise_if_needed(path)

        if "/" not in path:
            path = path.replace(".", "/")

        path = "/metadata/" + path

        # separator is now '/' and path is absolute
        return raise_if_needed(path)

    def _path_to_list(self, path):
        parts = path.split("/")
        if parts[0] == "":
            parts = parts[1:]
        return parts

    def get_value(self, path):
        # Read a value from the record using a path:
        # path is a string with keys separated by dots or slashes.
        # e.g. "metadata.updated" or "metadata/updated"
        # list indices are also supported, e.g. "metadata.tags.0"

        path = self.resolve_path(path, check=False)

        rec = self.record
        for p in self._path_to_list(path):
            if isinstance(rec, list):
                rec = rec[int(p)]
            elif isinstance(rec, dict):
                rec = rec[p]
            else:
                raise KeyError(f"Cannot get value for {path} in {self.record}. {p} is not a key in {rec}")
        return rec

    def set_value(self, path, value, type_=None, increment_update=False):
        path = self.resolve_path(path)
        return self.patch_value("add", path, value=value, type_=type_, increment_update=increment_update)

    def set_value_from_file(self, path, file):
        value = load_any_dict_format(file)
        self.set_value(path, value)

    def remove_value(self, path, increment_update=False):
        path = self.resolve_path(path)
        return self.patch_value("remove", path, increment_update=increment_update)

    def patch_value(self, op, path, value=None, type_=None, from_=None, increment_update=False):
        path = self.resolve_path(path)
        patch = {"op": op, "path": path}

        # if operation has a value, parse it and use it
        if op in ("add", "replace", "test"):
            value = parse_value(value, type_)
            patch["value"] = value

        # if has a from value, use it
        if from_ is not None:
            patch["from"] = from_

        patches = [patch]
        if "/" in path[1:]:
            parent_path = path.rsplit("/", 1)[0]
            parent_name = parent_path.rsplit("/", 1)[0]
            try:
                self.get_value(parent_path)
            except KeyError:
                if parent_name.isdigit():
                    patches = [{"op": "add", "path": parent_path, "value": []}] + patches
                else:
                    patches = [{"op": "add", "path": parent_path, "value": {}}] + patches

        if increment_update:
            updated = self.record["metadata"].get("updated", 0)
            patches = [{"op": "add", "path": "/metadata/updated", "value": updated + 1}] + patches

        LOG.debug(f"jsonpatch: {patches}")
        self.patch(patches)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.rest_collection}, {self.key})"
