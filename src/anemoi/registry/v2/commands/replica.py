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

from ..entry.replica import ReplicaCatalogueEntry, ReplicaCatalogueEntryList
from ..utils import list_to_dict
from . import Command

LOG = logging.getLogger(__name__)


class Replica(Command):
    """Manage dataset replicas (locations) across sites."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "PATH",
            help="Local path to the dataset (used with --register).",
            nargs="?",
        )
        command_parser.add_argument(
            "--dataset-name",
            help="Name of the dataset in the catalogue.",
            metavar="NAME",
        )
        command_parser.add_argument(
            "--site",
            help="The site (platform) name for the replica.",
            metavar="SITE",
        )
        command_parser.add_argument(
            "--uri-pattern",
            help="Path pattern for the location using {name}, e.g. 's3://ml-datasets/{name}.zarr'.",
            metavar="PATTERN",
        )

        command_parser.add_argument(
            "--register",
            help="Register a replica location for a dataset.",
            action="store_true",
        )
        command_parser.add_argument(
            "--upload",
            help="Upload the dataset when registering. Requires --site and PATH.",
            action="store_true",
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove a replica location from the catalogue (without deleting the data).",
            action="store_true",
        )
        command_parser.add_argument(
            "--delete",
            help="Delete the replica data and remove the location from the catalogue.",
            action="store_true",
        )
        command_parser.add_argument(
            "--request-transfer",
            help="Create a task to transfer a dataset to a site.",
            action="store_true",
        )
        command_parser.add_argument(
            "--request-deletion",
            help="Create a task to delete a dataset replica from a site.",
            action="store_true",
        )

        command_parser.add_argument(
            "--list",
            help="List replicas. Optional key=value filters.",
            nargs="*",
            metavar="K=V",
        )
        command_parser.add_argument(
            "--list-fields",
            help="Comma-separated field names to display.",
            type=lambda s: [f.strip() for f in s.split(",")],
            metavar="FIELDS",
        )
        command_parser.add_argument(
            "--list-format",
            help="Output format for --list.",
            choices=["text", "csv", "json", "rich"],
            default="rich",
        )

    def _get_replica_entry(self, args):
        name = args.dataset_name
        site = args.site

        if name is None and args.PATH is not None:
            name = os.path.splitext(os.path.basename(args.PATH))[0]
        if name is None:
            raise ValueError("--dataset-name is required (or provide a PATH).")
        if site is None:
            raise ValueError("--site is required.")

        return ReplicaCatalogueEntry(dataset_name=name, site=site)

    def run(self, args):
        if args.list is not None:
            return self._run_list(args)

        if args.register:
            return self._run_register(args)

        if args.unregister:
            return self._run_unregister(args)

        if args.delete:
            return self._run_delete(args)

        if args.request_transfer:
            return self._run_request_transfer(args)

        if args.request_deletion:
            return self._run_request_deletion(args)

        raise ValueError(
            "Please specify an action: --register, --unregister, --delete, "
            "--request-transfer, --request-deletion, or --list."
        )

    def _run_register(self, args):
        entry = self._get_replica_entry(args)
        entry.register(
            source_path=args.PATH,
            uri_pattern=args.uri_pattern,
            upload=args.upload,
        )

    def _run_unregister(self, args):
        entry = self._get_replica_entry(args)
        entry.unregister()

    def _run_delete(self, args):
        entry = self._get_replica_entry(args)
        entry.delete()

    def _run_request_transfer(self, args):
        entry = self._get_replica_entry(args)
        uuid = entry.request_transfer(uri_pattern=args.uri_pattern)
        print(uuid)

    def _run_request_deletion(self, args):
        entry = self._get_replica_entry(args)
        uuid = entry.request_deletion()
        print(uuid)

    def _run_list(self, args):
        from requests.exceptions import HTTPError

        from .base import _handle_field_error, format_list_output

        filters = list_to_dict(args.list) if args.list else {}
        if args.dataset_name:
            filters["name"] = args.dataset_name
        if args.site:
            filters["site"] = args.site

        fields = args.list_fields or ["name", "site", "path"]
        fmt = args.list_format

        # Pass requested fields to the server for validation + projection
        filters["fields"] = ",".join(fields)

        try:
            replicas = ReplicaCatalogueEntryList(**filters).get()
        except HTTPError as e:
            _handle_field_error(e)
            raise
        format_list_output(replicas, fields, fmt)


command = Replica
