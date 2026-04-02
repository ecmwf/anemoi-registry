# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..entry.training import TrainingCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Trainings(BaseCommand):
    """Manage trainings in the catalogue. Register, unregister, add weights, add plots, etc."""

    internal = True
    timestamp = True
    entry_class = TrainingCatalogueEntry
    kind = "training"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME", help="Name of a training.", nargs="?")
        command_parser.add_argument(
            "--register",
            help=(
                f"Register the {self.kind} in the catalogue. "
                "PATH is a JSON config file; NAME is deduced from the file if not given. "
                "If PATH is omitted, an empty entry is created with the given NAME."
            ),
            metavar="PATH",
            nargs="?",
            const=True,
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting the training from other locations)",
            action="store_true",
        )
        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")
        command_parser.add_argument(
            "--add-weights",
            nargs="+",
            help=(
                "Add weights to the experiment and upload them do s3."
                "Skip upload if these weights are already uploaded."
            ),
            metavar="FILE",
        )
        tail = command_parser.add_argument_group()
        self.add_set_get_remove_metadata_arguments(tail)
        self.add_list_arguments(tail)

    def run(self, args):
        if args.list is not None:
            return self.run_list(args)

        if args.register and args.register is not True:
            # --register PATH: load from the JSON file
            entry = self.entry_class.load_from_path(args.register)
        else:
            entry = self.get_entry(args)

        if entry is not None and args.unregister:
            entry.unregister()
        if args.register:
            entry.register(overwrite=args.overwrite)
        self.set_get_remove_metadata(entry, args)


command = Trainings
