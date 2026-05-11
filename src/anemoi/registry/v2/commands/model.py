# (C) Copyright 2026 Anemoi contributors.
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


class Model(BaseCommand):
    """Manage models (weights) in the catalogue.

    Examples:
      anemoi-registry model --register /data/my-model.ckpt
      anemoi-registry model my-model --register /data/my-model.ckpt --no-upload
    """

    internal = True
    timestamp = True
    entry_class = WeightCatalogueEntry
    kind = "model"

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "NAME", help="Name of the model. Optional when --register PATH is given (deduced from path).", nargs="?"
        )
        command_parser.add_argument(
            "--register",
            help="Register the model in the catalogue and upload it. NAME is deduced from PATH if not given. Use --no-upload to skip the upload.",
            metavar="PATH",
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting it from its actual locations). Ignore all other options.",
            action="store_true",
        )
        command_parser.add_argument(
            "--no-upload",
            dest="upload",
            action="store_false",
            help="Skip upload when registering (register in catalogue only).",
        )
        command_parser.set_defaults(upload=True)
        command_parser.add_argument("--overwrite", help="Overwrite any existing model.", action="store_true")
        # command_parser.add_argument(
        #     "--delete",
        #     action="store_true",
        #     help="Delete the model from the catalogue and from all its locations (not implemented).",
        # )
        command_parser.add_argument(
            "--type", help="Type of the model weights, such as 'training' or 'inference'.", default="training"
        )
        command_parser.add_argument("--download", help="Download the model from the catalogue to PATH.", metavar="PATH")

        tail = command_parser.add_argument_group()
        tail.add_argument("--url", help="Print the URL of the model.", action="store_true")
        tail.add_argument("--view", help="Open the URL of the model in a browser.", action="store_true")
        self.add_set_get_remove_metadata_arguments(tail)
        self.add_list_arguments(tail)

    def run(self, args):
        if args.list is not None:
            return self.run_list(args)

        if not args.NAME:
            if args.register:
                import os

                args.NAME = os.path.splitext(os.path.basename(args.register.rstrip("/")))[0]
            else:
                raise ValueError("NAME is required (or provide --register PATH to deduce it).")

        if args.register:
            entry = self.entry_class.load_from_path(args.register)
        else:
            entry = self.get_entry(args)

        if args.unregister:
            entry.unregister()
            return

        if args.register:
            entry.register(overwrite=args.overwrite, upload=args.upload)
        self.set_get_remove_metadata(entry, args)

        if args.url:
            print(entry.url)
        if args.view:
            import webbrowser

            webbrowser.open(entry.url)

        if args.download:
            entry.download(args.download, platform="ewc")


command = Model
