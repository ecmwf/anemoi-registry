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

import argparse
import logging
import os

from ..entry.dataset import DatasetCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Datasets(BaseCommand):
    """Manage datasets in the catalogue. Register, add locations, set status, etc."""

    internal = True
    timestamp = True
    entry_class = DatasetCatalogueEntry
    kind = "dataset"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME_OR_PATH", help="The name or the path of a dataset.")
        command_parser.add_argument("--register", help="Register a dataset in the catalogue.", action="store_true")
        command_parser.add_argument(
            "--unregister",
            help="Remove a dataset from catalogue (without deleting it from its locations). Ignore all other options.",
            action="store_true",
        )
        command_parser.add_argument("--url", help="Print the URL of the dataset.", action="store_true")
        command_parser.add_argument("--set-status", help="Set the status to the dataset.", metavar="STATUS")
        command_parser.add_argument(
            "--set-recipe", help="Set the recipe file to [re-]build the dataset.", metavar="FILE"
        )
        command_parser.add_argument(
            "--add-local",
            help=("Platform name to add a new location to the NAME_OR_PATH. " "Requires that NAME_OR_PATH is a path."),
            metavar="PLATFORM",
        )

        command_parser.add_argument("--add-location", help="Platform name to add a new location.", metavar="PLATFORM")
        command_parser.add_argument(
            "--uri-pattern",
            help="Path of the new location using {name}, such as 's3://ml-datasets/{name}.zarr' . Requires a platform name in --add-location.",
            metavar="PATH",
        )
        command_parser.add_argument(
            "--upload",
            help="Upload the dataset. Requires a platform name in --add-location.",
            action=argparse.BooleanOptionalAction,
            default=False,
        )

        command_parser.add_argument("--remove-location", help="Platform name to remove.", metavar="PLATFORM")
        command_parser.add_argument(
            "--DELETE",
            help="Delete the dataset when removing a location. Requires --remove-location.",
            action="store_true",
        )

    def _run(self, entry, args):
        if entry is None:
            raise ValueError(f"Dataset {args.NAME_OR_PATH} not found in the catalogue and path does not exists.")

        if args.unregister:
            entry.unregister()
            return

        if args.add_local and not os.path.exists(args.NAME_OR_PATH):
            raise ValueError(f"Path {args.NAME_OR_PATH} does not exists. Cannot use --add-local.")

        if args.upload:
            if not os.path.exists(args.NAME_OR_PATH):
                raise ValueError(f"Path {args.NAME_OR_PATH} does not exists. Cannot use --upload.")
            if not args.add_location:
                raise ValueError("Cannot use --upload without --add-location.")

        if args.uri_pattern is not None:
            if not args.add_location:
                raise ValueError("Cannot use --uri-pattern without --add-location.")
            if "{name}" not in args.uri_pattern:
                raise ValueError(f"URI pattern {args.uri_pattern} does not contain '{{name}}'")

        # order matters
        self.process_task(entry, args, "register")
        self.process_task(entry, args, "set_recipe")
        self.process_task(entry, args, "set_status")
        self.process_task(entry, args, "remove_location", delete=args.DELETE)

        if args.add_local:
            entry.add_location(args.add_local, path=args.NAME_OR_PATH)

        if args.upload or args.add_location:
            path = entry.build_location_path(platform=args.add_location, uri_pattern=args.uri_pattern)
            if args.upload:
                entry.upload(source=args.NAME_OR_PATH, target=path, platform=args.add_location)
            if args.add_location:
                LOG.info(f"Adding location to {args.add_location}: {path}")
                entry.add_location(platform=args.add_location, path=path)

        if args.url:
            print(entry.url)


command = Datasets
