# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..entry.replica import ReplicaCatalogueEntry
from ..entry.replica import ReplicaCatalogueEntryList
from ..utils import list_to_dict
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Replica(BaseCommand):
    """Manage dataset replicas (locations) across sites."""

    internal = True
    timestamp = True
    entry_class = ReplicaCatalogueEntry
    kind = "replica"

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "SITE",
            nargs="?",
            help="Site (platform) name. Required for all actions except --list.",
        )
        command_parser.add_argument(
            "NAME",
            nargs="?",
            help="Dataset name in the catalogue. Required for all actions except --list.",
        )

        command_parser.add_argument(
            "--register",
            metavar="PATH",
            help="Register a replica location in the catalogue (no data is moved). PATH is the path of the dataset on the site.",
        )
        command_parser.add_argument(
            "--unregister",
            action="store_true",
            help="Remove a replica location from the catalogue (data is kept).",
        )
        command_parser.add_argument(
            "--upload",
            metavar="PATH",
            help=(
                "Upload a local dataset to remote storage and register the replica. "
                "PATH is the local zarr path; the dataset must already be registered in the catalogue "
                "(anemoi-registry dataset --register PATH). "
                "Example: anemoi-registry replica ewc my-dataset --upload /data/my-dataset.zarr"
            ),
        )
        command_parser.add_argument(
            "--target-uri",
            metavar="URI",
            help=(
                "Where to write the data during upload (may use {name}). "
                "Default: from server config (datasets_uri_pattern)."
            ),
        )
        command_parser.add_argument(
            "--threads",
            type=int,
            default=2,
            help="Number of transfer threads for upload (default: 2).",
        )
        command_parser.add_argument(
            "--request-delete",
            action="store_true",
            help=(
                "Schedule deletion of a replica via the task runner "
                "(same as the catalogue delete button): creates a delete task; "
                "the task runner will delete the data and unregister the replica."
            ),
        )
        command_parser.add_argument(
            "--request-transfer",
            nargs="?",
            const=True,
            metavar="SOURCE_SITE",
            help="Create a task to transfer the replica to SITE from SOURCE_SITE.",
        )
        tail = command_parser.add_argument_group()
        tail.add_argument("--url", help="Print the URL of the replica.", action="store_true")
        tail.add_argument("--view", help="Open the URL of the replica in a browser.", action="store_true")
        self.add_list_arguments(tail)

    def run(self, args):
        if args.list is not None:
            if args.NAME or args.SITE:
                raise ValueError("--list does not take NAME or SITE positional arguments.")
            return self._run_list(args)

        # All actions require exactly SITE + NAME.
        if not args.SITE or not args.NAME:
            raise ValueError("SITE and NAME are required for this action. " "Use --list to list replicas.")

        if args.upload:
            return self._run_upload(args)

        if args.register:
            return self._run_register(args)
        if args.unregister:
            return self._run_unregister(args)
        if args.request_delete:
            return self._run_request_delete(args)
        if args.request_transfer is not None:
            return self._run_request_transfer(args)

        entry = ReplicaCatalogueEntry(dataset_name=args.NAME, site=args.SITE)
        if args.url:
            print(entry.url)
        if args.view:
            import webbrowser

            webbrowser.open(entry.url)

        if not args.url and not args.view:
            raise ValueError(
                "Please specify an action: --register, --unregister, --upload, "
                "--request-delete, --request-transfer, --url, --view, or --list."
            )

    def _run_register(self, args):
        ReplicaCatalogueEntry(dataset_name=args.NAME, site=args.SITE).register(source_path=args.register)

    def _run_unregister(self, args):
        records = list(ReplicaCatalogueEntryList(name=args.NAME, site=args.SITE))
        if not records:
            raise ValueError(f"Replica '{args.NAME}@{args.SITE}' not found in the catalogue.")
        records[0].unregister()

    def _run_upload(self, args):
        # target_uri=None → entry reads datasets_uri_pattern from server config
        # registered_uri=None → entry defaults to target_uri
        ReplicaCatalogueEntry(dataset_name=args.NAME, site=args.SITE).register(
            source_path=args.upload,
            target_uri=args.target_uri,
            upload=True,
            threads=args.threads,
        )

    def _run_request_delete(self, args):
        uuid = ReplicaCatalogueEntry(dataset_name=args.NAME, site=args.SITE).request_deletion()
        LOG.info(f"Deletion task created: {uuid}")

    def _run_request_transfer(self, args):
        if args.request_transfer is True:
            raise NotImplementedError(
                "--request-transfer requires a SOURCE_SITE. "
                "Example: anemoi-registry replica ewc my-dataset --request-transfer lumi"
            )
        ReplicaCatalogueEntry(dataset_name=args.NAME, site=args.SITE).request_transfer(from_site=args.request_transfer)

    def _run_list(self, args):
        from requests.exceptions import HTTPError

        from .base import _handle_field_error
        from .base import format_list_output

        filters = list_to_dict(args.list) if args.list else {}

        fields = args.list_fields or ["name", "site", "path"]
        fmt = args.list_format
        filters["fields"] = ",".join(fields)
        sort = getattr(args, "list_sort", None)
        if sort:
            filters["sort"] = sort

        try:
            replicas = ReplicaCatalogueEntryList(**filters).get()
        except HTTPError as e:
            _handle_field_error(e)
            raise
        format_list_output(replicas, fields, fmt)


command = Replica
