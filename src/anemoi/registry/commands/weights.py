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

from ..entry.weights import WeightCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Weights(BaseCommand):
    """Manage weights in the catalogue. Register, add locations, etc."""

    internal = True
    timestamp = True
    entry_class = WeightCatalogueEntry
    kind = "weights"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME_OR_PATH", help=f"Name or path of a {self.kind}.")
        command_parser.add_argument(
            "--register", help=f"Register the {self.kind} in the catalogue.", action="store_true"
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting it from its actual locations). Ignore all other options.",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")

        command_parser.add_argument("--add-location", help="Platform to add location to the weights.")
        command_parser.add_argument("--location-path", help="Path of the new location using {{uuid}}.", metavar="PATH")
        command_parser.add_argument("--overwrite", help="Overwrite any existing weights.", action="store_true")
        command_parser.add_argument("--url", help="Print the URL of the dataset.", action="store_true")

    def _run(self, entry, args):
        if args.unregister:
            entry.unregister()
            return
        self.process_task(entry, args, "register", overwrite=args.overwrite)
        self.process_task(entry, args, "add_location", path=args.location_path)
        if args.url:
            print(entry.url)


command = Weights
