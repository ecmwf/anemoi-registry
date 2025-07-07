# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


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
        command_parser.add_argument("NAME_OR_PATH", help="Name or path of weights.")
        command_parser.add_argument(
            "--type", help="Type of the weights, such as 'training' or 'inference'.", default="training"
        )
        command_parser.add_argument("--register", help="Register the weights in the catalogue.", action="store_true")
        command_parser.add_argument("--download", help="Download the weights from the catalogue.")

        group = command_parser.add_mutually_exclusive_group()
        group.add_argument("--upload", dest="upload", action="store_true", help="Enable upload (default)")
        group.add_argument("--no-upload", dest="upload", action="store_false", help="Disable upload")
        command_parser.set_defaults(upload=True)

        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting it from its actual locations). Ignore all other options.",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the weights from the catalogue and from any other location", action="store_true")
        self.add_set_get_remove_metadata_arguments(command_parser)

        command_parser.add_argument("--add-location", help="Platform to add location to the weights.")
        command_parser.add_argument("--location-path", help="Path of the new location using {{uuid}}.", metavar="PATH")
        command_parser.add_argument("--overwrite", help="Overwrite any existing weights.", action="store_true")
        command_parser.add_argument("--url", help="Print the URL of the dataset.", action="store_true")
        command_parser.add_argument("--view", help="Open the URL of the weights in a browser.", action="store_true")

    def run(self, args):
        entry = self.get_entry(args)
        if args.unregister:
            entry.unregister()
            return
        self.process_task(entry, args, "register", overwrite=args.overwrite, upload=args.upload)
        self.process_task(entry, args, "add_location", path=args.location_path)
        self.set_get_remove_metadata(entry, args)

        if args.url:
            print(entry.url)
        if args.view:
            import webbrowser

            webbrowser.open(entry.url)

        self.process_task(entry, args, "download", platform="ewc")


command = Weights
