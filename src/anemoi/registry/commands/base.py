# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Command place holder. Delete when we have real commands."""

import json
import logging
import os

import yaml

from ..entry import VALUES_PARSERS
from ..entry import CatalogueEntryNotFound
from . import Command

LOG = logging.getLogger(__name__)


class BaseCommand(Command):
    internal = True
    timestamp = True

    def is_path(self, name_or_path):
        return os.path.exists(name_or_path)

    def is_identifier(self, name_or_path):
        try:
            self.entry_class(key=name_or_path)
            return True
        except CatalogueEntryNotFound:
            return False

    def process_task(self, entry, args, k, func_name=None, /, _skip_if_not_found=False, **kwargs):
        """Call the method `k` on the entry object.
        The args/kwargs given to the method are extracted from from the argument `k` in the `args` object.

        Additionally the argument `k` is casted to the correct type,
        depending on if this is a string, int, float, list or dict, or a boolean.

        The provided **kwargs are also passed to the method.
        The method name can be changed by providing the `func_name` argument.
        """
        if entry is None and _skip_if_not_found:
            LOG.warning(f"Cannot find entry {args.NAME_OR_PATH}. Skipping {k}.")
            return

        assert isinstance(k, str), k
        if func_name is None:
            func_name = k

        v = getattr(args, k)

        if v is None:
            return
        if v is True:
            LOG.debug(f"{entry.key} : Processing task {k}")
            return getattr(entry, func_name)(**kwargs)
        if v is False:
            return
        if isinstance(v, (str, int, float)):
            LOG.debug(f"{entry.key} : Processing task {k} with {v}")
            return getattr(entry, func_name)(v, **kwargs)
        if isinstance(v, list):
            v_str = ", ".join(str(x) for x in v)
            LOG.debug(f"{entry.key} : Processing task {k} with {v_str}")
            return getattr(entry, func_name)(*v, **kwargs)
        if isinstance(v, dict):
            v_str = ", ".join(f"{k_}={v_}" for k_, v_ in v.items())
            LOG.debug(f"{entry.key} : Processing task {k} with {v_str}")
            return getattr(entry, func_name)(**v, **kwargs)
        raise ValueError(f"Invalid task {k}={v}. type(v)= {type(v)}")

    def run(self, args):
        LOG.debug(f"anemoi-registry args: {args}")
        name_or_path = args.NAME_OR_PATH
        entry = self.get_entry(name_or_path)
        self._run(entry, args)

    def get_entry(self, name_or_path):
        if self.is_path(name_or_path):
            LOG.debug(f"Found local {self.kind} at {name_or_path}")
            return self.entry_class(path=name_or_path)

        if self.is_identifier(name_or_path):
            LOG.debug(f"Processing {self.kind} with identifier '{name_or_path}'")
            return self.entry_class(key=name_or_path)

    def run_from_identifier(self, *args, **kwargs):
        raise NotImplementedError()

    def run_from_path(self, *args, **kwargs):
        raise NotImplementedError()

    def set_get_remove_metadata(self, entry, args):

        if args.get_metadata:
            value = entry.get_value(args.get_metadata[0])
            if len(args.get_metadata) > 1:
                type_ = args.get_metadata[1]
                value = dict(str=str, yaml=yaml.safe_dump, json=json.dumps)[type_](value)
            print(value)

        if args.set_metadata:
            path, value = args.set_metadata[0].split("=", 1)
            type_ = args.set_metadata[1] if len(args.set_metadata) > 1 else None
            entry.set_value(path, value, type_=type_, increment_update=True)

        if args.remove_metadata:
            entry.remove_value(args.remove_metadata, increment_update=True)

    def add_set_get_remove_metadata_arguments(self, command_parser):
        command_parser.add_argument(
            "--get-metadata",
            help=(
                f"Get a metadata value from the {self.kind} catalogue record (KEY, [TYPE]). "
                "KEY is a '.' separated path to the value. "
                "TYPE is the output format : str (default), yaml, json."
            ),
            nargs="+",
            metavar=("KEY", "TYPE"),
        )
        command_parser.add_argument(
            "--set-metadata",
            help=(
                f"Set a metadata value to the {self.kind} catalogue record (KEY=VALUE, [TYPE]). "
                "KEY is a '.' separated path to the value. "
                f"TYPE is the input type : {', '.join(VALUES_PARSERS.keys())}. "
                "Default type is 'str'. "
                "TYPE 'int', 'float', 'bool', 'datetime', 'timedelta' cast the VALUE before storing it. "
                "TYPE 'json' and 'yaml' parse the VALUE before storing it. "
                "TYPE 'path' reads the file provided as VALUE (.json, .yaml, etc). "
                "TYPE 'stdin' reads the value from the standard input, ignoring the VALUE. "
            ),
            nargs="+",
            metavar=("KEY=VALUE", "TYPE"),
        )
        command_parser.add_argument(
            "--remove-metadata",
            help=f"Delete a metadata value to the {self.kind} catalogue record (KEY)",
            metavar="KEY",
        )
