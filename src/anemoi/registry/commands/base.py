# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Command place holder. Delete when we have real commands."""

import logging
import os

from anemoi.registry import config

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
        def resolve_path(path, check=True):
            # Add /metadata/ to the path if it is not there,
            # the rest of the catalogue record should not be changed.
            # But allow to do is anyway if the user configuration allows it.

            def raise_if_needed():
                if check and not config().get("allow_edit_entries"):
                    raise ValueError(
                        "Editing entries is not allowed, only metadata can be changed. "
                        "Please set value to true in your config file if you know what you are doing."
                    )

            if path.startswith("../"):
                raise_if_needed()
                return path[3:]
            if path.startswith("..."):
                raise_if_needed()
                return path[3:]
            if path.startswith(".."):
                raise_if_needed()
                return path[2:]

            return path if path.startswith("/metadata/") else "/metadata/" + path

        if args.get_metadata:
            args.get_metadata = resolve_path(args.get_metadata, check=False)
            print(entry.get_value(args.get_metadata))
        if args.set_metadata:
            args.set_metadata[0] = resolve_path(args.set_metadata[0])
            entry.set_value(*args.set_metadata, increment_update=True)
        if args.remove_metadata:
            args.remove_metadata = resolve_path(args.remove_metadata)
            entry.remove_value(args.remove_metadata, increment_update=True)
        # if args.patch:
        #     if len(args.patch) not in (2, 3, 4):
        #         raise ValueError(f"Invalid patch {args.patch}")
        #     entry.patch_value(*args.patch, increment_update=True)

    def add_set_get_remove_metadata_arguments(self, command_parser):
        command_parser.add_argument(
            "--get-metadata",
            help=f"Get a metadata value from the {self.kind} catalogue record",
            metavar="KEY",
        )
        command_parser.add_argument(
            "--set-metadata",
            help=f"Set a metadata value to the {self.kind} catalogue record (KEY, VALUE, [TYPE])",
            nargs="+",
        )
        command_parser.add_argument(
            "--remove-metadata",
            help=f"Delete a metadata value to the {self.kind} catalogue record (KEY)",
        )
        # command_parser.add_argument(
        #    "--patch",
        #    help="Patch the metadata to the {self.kind} catalogue record (OP, KEY, [VALUE], [TYPE])",
        #    nargs="+",
        # )
