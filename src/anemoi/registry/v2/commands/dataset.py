# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..entry.dataset import DatasetCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Datasets(BaseCommand):
    """Manage datasets in the catalogue. Register, set status, set recipe, etc."""

    internal = True
    timestamp = True
    entry_class = DatasetCatalogueEntry
    kind = "dataset"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME_OR_PATH", help="The name or the path of a dataset.", nargs="?")
        self.add_list_arguments(command_parser)
        command_parser.add_argument("--register", help="Register a dataset in the catalogue.", action="store_true")
        command_parser.add_argument(
            "--unregister",
            help="Remove a dataset from catalogue (without deleting it from its locations). Ignore all other options.",
            action="store_true",
        )
        command_parser.add_argument("--url", help="Print the URL of the dataset.", action="store_true")
        command_parser.add_argument(
            "--view", help=f"Open the URL of the {self.kind} in a browser.", action="store_true"
        )

        self.add_set_get_remove_metadata_arguments(command_parser)

        command_parser.add_argument("--set-status", help="Set the status to the dataset.", metavar="STATUS")
        command_parser.add_argument(
            "--set-recipe", help="Set the recipe file to [re-]build the dataset.", metavar="FILE"
        )

    def run(self, args):
        if args.list is not None:
            return self.run_list(args)
        entry = self.get_entry(args)
        if entry is None:
            raise ValueError(f"Dataset {args.NAME_OR_PATH} not found in the catalogue and path does not exist.")

        if args.unregister:
            entry.unregister()
            return

        # order matters
        self.process_task(entry, args, "register")
        self.process_task(entry, args, "set_recipe")
        self.process_task(entry, args, "set_status")
        self.set_get_remove_metadata(entry, args)

        if args.url:
            print(entry.url)
        if args.view:
            import webbrowser

            webbrowser.open(entry.url)


command = Datasets
