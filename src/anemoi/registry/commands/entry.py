#!/usr/bin/env python
# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

"""Command place holder. Delete when we have real commands.

"""

import json
import logging
import os
import subprocess
from tempfile import TemporaryDirectory

import jsonpatch
import yaml

from anemoi.registry.rest import Rest

from . import Command

LOG = logging.getLogger(__name__)


class Entry(Command):
    """Admin tool. Manage entries in the catalogue."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument("path", help="API path to the entry.")

        group = command_parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "--dump",
            action="store_true",
            help=(
                "Extract the metadata from the entry and print it to the standard output"
                " or the file specified by ``--output``, in JSON or YAML format."
            ),
        )
        group.add_argument(
            "--load",
            action="store_true",
            help="Set the metadata in the entry from the content of a file specified by the ``--input`` argument.",
        )

        group.add_argument(
            "--edit",
            action="store_true",
            help="Edit the metadata in place, using the specified editor. See the ``--editor`` argument for more information.",
        )

        group.add_argument("--remove", action="store_true", help="Remove the entry.")

        command_parser.add_argument("--input", help="The output file name to be used by the ``--load`` option.")
        command_parser.add_argument("--output", help="The output file name to be used by the ``--dump`` option.")
        command_parser.add_argument(
            "--create",
            action="store_true",
            help="Create the entry if it does not exist., use with --load",
        )

        command_parser.add_argument(
            "--editor",
            help="Editor to use for the ``--edit`` option. Default to ``$EDITOR`` if defined, else ``vi``.",
            default=os.environ.get("EDITOR", "vi"),
        )

        command_parser.add_argument(
            "--json", action="store_true", help="Use the JSON format with ``--dump`` and ``--edit``."
        )

        command_parser.add_argument(
            "--yaml", action="store_true", help="Use the YAML format with ``--dump`` and ``--edit``."
        )

    def run(self, args):
        path = args.path
        if "/" not in path[1:] or not path.startswith("/"):
            raise ValueError("Invalid API path {path}")

        _, collection, *_ = path.split("/")
        if collection not in ("datasets", "experiments", "weights", "tasks"):
            LOG.warning(f"Unknown collection {collection}")

        if args.edit:
            return self.edit(args)

        if args.remove:
            return self.remove(args)

        if args.dump:
            return self.dump(args)

        if args.load:
            return self.load(args)

    def edit(self, args):
        rest = Rest()

        if args.json:
            ext = "json"
            dump = json.dump
            load = json.load
            kwargs = {"indent": 4, "sort_keys": True}
        else:
            ext = "yaml"
            dump = yaml.dump
            load = yaml.safe_load
            kwargs = {"default_flow_style": False}

        with TemporaryDirectory() as temp_dir:

            path = os.path.join(temp_dir, f"anemoi-registry-edit.{ext}")

            metadata = rest.get(args.path)

            with open(path, "w") as f:
                dump(metadata, f, **kwargs)

            subprocess.check_call([args.editor, path])

            with open(path) as f:
                edited = load(f)

            if edited != metadata:
                patch = jsonpatch.make_patch(metadata, edited)
                patch = list(patch)
                LOG.debug(f"Applying patch to {args.path}: {patch}")
                rest.patch(args.path, patch)
                LOG.info(f"{args.path} has been updated.")
            else:
                LOG.info("No changes made.")

    def dump(self, args):
        rest = Rest()

        if args.output:
            file = open(args.output, "w")
        else:
            file = None

        metadata = rest.get(args.path)

        if args.yaml:
            print(yaml.dump(metadata, indent=2, sort_keys=True), file=file)
            return

        if args.json or True:
            print(json.dumps(metadata, indent=4, sort_keys=True), file=file)
            return

    def load(self, args):
        rest = Rest()

        if args.input is None:
            raise ValueError("Please specify a value for --input")

        _, ext = os.path.splitext(args.input)
        if ext == ".json" or args.json:
            with open(args.input) as f:
                edited = json.load(f)

        elif ext in (".yaml", ".yml") or args.yaml:
            with open(args.input) as f:
                edited = yaml.safe_load(f)

        else:
            raise ValueError(f"Unknown file extension {ext}. Please specify --json or --yaml")

        if rest.exists(args.path):
            # if the entry exists, we patch it.
            metadata = rest.get(args.path)
            patch = jsonpatch.make_patch(metadata, edited)
            patch = list(patch)
            LOG.debug(f"Applying patch to {args.path}: {patch}")
            rest.patch(args.path, patch)
            LOG.info(f"{args.path} has been updated.")

        else:
            # if the entry does not exist, we post it if requested.
            if not args.create:
                LOG.error(f"Entry in {args.path} does not exists. Using --create to create it.")
                raise ValueError(f"Entry in {args.path} does not exists. Using --create to create it.")

            _, collection, *_ = args.path.split("/")
            res = rest.post(collection, edited)
            LOG.info(f"Entry in {collection} has been created : {res}.")

    def remove(self, args):
        path = args.path
        if not path.startswith("/"):
            path = "/" + path
        rest = Rest()
        rest.delete(path)
        LOG.info(f"{path} has been deleted.")


command = Entry
