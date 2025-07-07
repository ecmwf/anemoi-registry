# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os

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
        command_parser.add_argument("NAME_OR_PATH", help="Name of a training of a path of a training config file.")
        command_parser.add_argument(
            "--register", help=f"Register the {self.kind} in the catalogue.", action="store_true"
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting the training from other locations)",
            action="store_true",
        )
        command_parser.add_argument(
            "--set-key",
            nargs=2,
            help="Set VALUE in the KEY to the training catalogue. Replace existing value.",
            metavar=("KEY", "VALUE"),
        )
        command_parser.add_argument(
            "--set-key-json",
            nargs=2,
            help="Set the content of a FILE in the KEY to the training catalogue. Replace existing value.",
            metavar=("KEY", "FILE"),
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

    def is_path(self, name_or_path):
        if not os.path.exists(name_or_path):
            return False
        if not name_or_path.endswith(".json"):
            return False
        return True

    def run(self, args):
        entry = self.get_entry(args)
        self.process_task(entry, args, "unregister", _skip_if_not_found=True)
        self.process_task(entry, args, "register", overwrite=args.overwrite)
        self.process_task(entry, args, "set_key")
        self.process_task(entry, args, "set_key_json")


command = Trainings
