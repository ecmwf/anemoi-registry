# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

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
            "NAME",
            help="Name of an experiment.",
            nargs="?",
        )
        command_parser.add_argument(
            "--register", help=f"Register the {self.kind} in the catalogue.", action="store_true"
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting the experiment from other locations)",
            action="store_true",
        )
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
            help="Set KEY to VALUE. Use --run-number to scope to a specific run.",
            metavar=("KEY", "VALUE"),
        )
        command_parser.add_argument(
            "--set-key-json",
            nargs=2,
            help="Set KEY to the parsed contents of FILE (JSON/YAML). Use --run-number to scope to a specific run.",
            metavar=("KEY", "FILE"),
        )

        command_parser.add_argument(
            "--set-archive",
            help="Input file to register as an archive metadata file to the catalogue. Use --run-number and --archive-platform to scope.",
            metavar="FILE",
        )
        command_parser.add_argument(
            "--get-archive",
            help="Output file to save the archive metadata from the catalogue. Merges across run numbers when --run-number is 'all'. Use --run-number and --archive-platform to scope.",
            metavar="FILE",
        )
        command_parser.add_argument(
            "--remove-archive",
            help="Delete the archive metadata. Use --run-number and --archive-platform to scope.",
            action="store_true",
        )
        command_parser.add_argument(
            "--archive-moved",
            help="Re-register an archive from platform OLD to platform NEW in the catalogue (no data is moved). Use --run-number to scope.",
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
            help="The run number of the experiment. Relevant for --set-key, --set-key-json, --set-archive, --get-archive, and --remove-archive. Can be 'all' or 'latest' when applicable.",
            metavar="N",
        )
        command_parser.add_argument(
            "--archive-extra-metadata", help="Extra metadata. A list of key=value pairs.", nargs="+", default={}
        )

        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")

        tail = command_parser.add_argument_group()
        tail.add_argument("--url", help="Print the URL of the experiment.", action="store_true")
        tail.add_argument("--view", help=f"Open the URL of the {self.kind} in a browser.", action="store_true")
        self.add_set_get_remove_metadata_arguments(tail)
        self.add_list_arguments(tail)

    def run(self, args):
        if args.list is not None:
            return self.run_list(args)
        entry = self.get_entry(args)
        if entry is not None and args.delete_artefacts:
            entry.delete_artefacts()
        if entry is not None and args.unregister:
            entry.unregister()
        if args.add_weights:
            entry.add_weights(*args.add_weights)
        if args.register:
            entry.register(overwrite=args.overwrite)
        self.set_get_remove_metadata(entry, args)
        if args.add_plots:
            entry.add_plots(*args.add_plots)
        if args.set_key:
            entry.set_key(*args.set_key, run_number=args.run_number)
        if args.set_key_json:
            entry.set_key_json(*args.set_key_json, run_number=args.run_number)
        if args.set_archive:
            entry.set_archive(
                run_number=args.run_number,
                platform=args.archive_platform,
                overwrite=args.overwrite,
                extras=args.archive_extra_metadata,
            )
        if args.get_archive:
            entry.get_archive(args.get_archive, run_number=args.run_number, platform=args.archive_platform)
        if entry is not None and args.remove_archive:
            entry.remove_archive(run_number=args.run_number, platform=args.archive_platform)
        if entry is not None and args.archive_moved:
            entry.archive_moved(*args.archive_moved, run_number=args.run_number)
        if args.url:
            print(entry.url)


command = Experiments
