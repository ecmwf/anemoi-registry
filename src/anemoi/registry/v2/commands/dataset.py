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
        command_parser.add_argument("NAME", help="The name of a dataset.", nargs="?")
        command_parser.add_argument(
            "--register",
            help=(
                "Register a dataset in the catalogue. "
                "PATH is the local zarr path; NAME is deduced from the path basename if not given. "
                "Only the metadata is registered — no data is moved. "
                "To also upload the data to a remote site, use: "
                "anemoi-registry replica --upload PATH. "
                "Example: anemoi-registry dataset --register /data/my-dataset.zarr  "
                "         anemoi-registry dataset my-dataset --register /data/my-dataset.zarr"
            ),
            metavar="PATH",
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove a dataset from catalogue (without deleting it from its locations). Fails if replicas still exist; use -f to override. Ignores all other options.",
            action="store_true",
        )
        command_parser.add_argument(
            "-f",
            "--force",
            help="Force --unregister even if replicas still exist.",
            action="store_true",
        )

        command_parser.add_argument("--set-status", help="Set the status to the dataset.", metavar="STATUS")
        command_parser.add_argument(
            "--set-recipe",
            help="(Deprecated) Set the recipe file to [re-]build the dataset.",
            metavar="FILE",
        )
        tail = command_parser.add_argument_group()
        tail.add_argument("--url", help="Print the URL of the dataset.", action="store_true")
        tail.add_argument("--view", help=f"Open the URL of the {self.kind} in a browser.", action="store_true")
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
            # Load metadata from the zarr path
            entry = self.entry_class.load_from_path(args.register)
        else:
            entry = self.get_entry(args)

        if entry is None:
            raise ValueError(f"Dataset '{args.NAME}' not found in the catalogue.")

        if args.unregister:
            from ..entry.replica import ReplicaCatalogueEntryList

            replicas = list(ReplicaCatalogueEntryList(name=entry.key))
            if replicas:
                sites = [r.site for r in replicas]
                if not args.force:
                    raise ValueError(
                        f"Dataset '{entry.key}' still has replicas on: {', '.join(sites)}. "
                        "Unregister or delete the replicas first, or use -f to force."
                    )
                LOG.warning(f"Forcing unregister of '{entry.key}' with existing replicas on: {', '.join(sites)}.")
            entry.unregister()
            return

        # order matters
        if args.register:
            entry.register()
        if args.set_recipe:
            LOG.warning(
                "--set-recipe is deprecated. Use 'anemoi-registry update --catalogue-from-recipe RECIPE' instead."
            )
            entry.set_recipe(args.set_recipe)
        if args.set_status:
            entry.set_status(args.set_status)
        self.set_get_remove_metadata(entry, args)

        if args.url:
            print(entry.url)
        if args.view:
            import webbrowser

            webbrowser.open(entry.url)


command = Datasets
