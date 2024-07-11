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

import logging

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
        command_parser.add_argument("NAME_OR_PATH", help=f"The name or the path of a {self.kind}.")
        command_parser.add_argument("--register", help=f"Register a {self.kind} in the catalogue.", action="store_true")
        command_parser.add_argument(
            "--unregister",
            help=f"Remove a {self.kind} from catalogue (without deleting it from its locations)",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")
        command_parser.add_argument("--set-status", help="Set the status to the {self.kind}.")
        command_parser.add_argument("--set-recipe", help="Set the recipe file to [re-]build the {self.kind}.")
        command_parser.add_argument(
            "--add-location",
            nargs="+",
            help="Path to add a location to the dataset. Implies --platform",
        )
        command_parser.add_argument("--platform", help="Platform to add the location to.")

    def check_arguments(self, args):
        pass

    def _run(self, entry, args):
        # order matters
        self.process_task(entry, args, "unregister")
        self.process_task(entry, args, "register")
        # self.process_task(entry, args, "remove_location")
        self.process_task(entry, args, "add_location", platform=args.platform)
        self.process_task(entry, args, "set_recipe")
        self.process_task(entry, args, "set_status")


command = Datasets
