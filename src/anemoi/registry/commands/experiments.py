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
import os

from ..entry.experiment import ExperimentCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Experiments(BaseCommand):
    """Manage experiments in the catalogue. Register, unregister, add weights, add plots, etc."""

    internal = True
    timestamp = True
    entry_class = ExperimentCatalogueEntry
    kind = "experiment"

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "NAME_OR_PATH", help="Name of an experiment of a path of an experiment config file."
        )
        command_parser.add_argument(
            "--register", help=f"Register the {self.kind} in the catalogue.", action="store_true"
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting the experiment from other locations)",
            action="store_true",
        )
        command_parser.add_argument("--url", help="Print the URL of the experiment.", action="store_true")
        command_parser.add_argument(
            "--delete-artefacts",
            help="Remove experiments artefacts (such as plots)",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")

        command_parser.add_argument(
            "--add-weights",
            nargs="+",
            help=(
                "Add weights to the experiment and upload them do s3."
                "Skip upload if these weights are already uploaded."
            ),
            metavar="FILE",
        )
        command_parser.add_argument("--add-plots", nargs="+", help="Add plots to the experiment.", metavar="FILE")
        command_parser.add_argument(
            "--set-key",
            nargs=2,
            help="Set VALUE in the KEY to the experiment catalogue. Replace existing value.",
            metavar=("KEY", "VALUE"),
        )
        command_parser.add_argument(
            "--set-key-json",
            nargs=2,
            help="Set the content of a FILE in the KEY to the experiment catalogue. Replace existing value.",
            metavar=("KEY", "FILE"),
        )

        command_parser.add_argument(
            "--set-archive", help="Input file to register as an archive metadata file to the catalogue.", metavar="FILE"
        )
        command_parser.add_argument(
            "--get-archive",
            help="Output file to save the archive metadata file from the catalogue. Merge metadata file if there are multiple run numbers.",
            metavar="FILE",
        )
        command_parser.add_argument("--remove-archive", help="Delete the archive metadata.", action="store_true")
        command_parser.add_argument(
            "--archive-moved",
            help="When archive moved to a new location, move the metadata file and update the catalogue.",
            nargs=2,
            metavar=("OLD", "NEW"),
        )

        command_parser.add_argument(
            "--archive-platform",
            help="Archive platform. Only relevant for --set-archive and --get-archive and --remove-archive.",
            metavar="PLATFORM",
        )
        command_parser.add_argument(
            "--run-number",
            help="The run number of the experiment. Relevant --set-archive and --get-archive and --remove-archive. Can be 'all' or 'latest' when applicable.",
            metavar="N",
        )
        command_parser.add_argument(
            "--archive-extra-metadata", help="Extra metadata. A list of key=value pairs.", nargs="+", default={}
        )

        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")

    def is_path(self, name_or_path):
        if not os.path.exists(name_or_path):
            return False
        if not name_or_path.endswith(".yaml"):
            return False
        return True

    def _run(self, entry, args):
        self.process_task(entry, args, "delete_artefacts", _skip_if_not_found=True)
        self.process_task(entry, args, "unregister", _skip_if_not_found=True)
        self.process_task(entry, args, "register", overwrite=args.overwrite)
        self.process_task(entry, args, "add_weights")
        self.process_task(entry, args, "add_plots")
        self.process_task(entry, args, "set_key", run_number=args.run_number)
        self.process_task(entry, args, "set_key_json", run_number=args.run_number)
        self.process_task(
            entry,
            args,
            "set_archive",
            run_number=args.run_number,
            platform=args.archive_platform,
            overwrite=args.overwrite,
            extras=args.archive_extra_metadata,
        )
        self.process_task(entry, args, "get_archive", run_number=args.run_number, platform=args.archive_platform)
        self.process_task(entry, args, "remove_archive", run_number=args.run_number, platform=args.archive_platform)
        self.process_task(entry, args, "archive_moved", run_number=args.run_number)
        if args.url:
            print(entry.url)


command = Experiments
