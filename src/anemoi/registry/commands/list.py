# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime
import logging

from anemoi.utils.humanize import bytes_to_human
from anemoi.utils.humanize import json_pretty_dump
from anemoi.utils.humanize import when
from anemoi.utils.text import table

from anemoi.registry.rest import RestItemList
from anemoi.registry.utils import list_to_dict

from . import Command

LOG = logging.getLogger(__name__)


class List(Command):
    """List elements in the catalogue."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        sub_parser = command_parser.add_subparsers(dest="subcommand")

        experiment = sub_parser.add_parser(
            "experiments",
            help="List experiments in the catalogue, for admin and debug purposes Current output is JSON and may change.",
        )
        experiment.add_argument(
            "filter", nargs="*", help="Filter experiments with a list of key=value.", metavar="key=value"
        )
        experiment.add_argument("--json", help="Output as JSON", action="store_true")

        checkpoint = sub_parser.add_parser("weights", help="List weights in the catalogue.")
        checkpoint.add_argument(
            "filter", nargs="*", help="Filter weights with a list of key=value.", metavar="key=value"
        )
        checkpoint.add_argument("--json", help="Output as JSON", action="store_true")

        training = sub_parser.add_parser(
            "trainings",
            help="List trainings in the catalogue, for admin and debug purposes Current output is JSON and may change.",
        )
        training.add_argument(
            "filter", nargs="*", help="Filter trainings with a list of key=value.", metavar="key=value"
        )
        training.add_argument("--json", help="Output as JSON", action="store_true")

        dataset = sub_parser.add_parser("datasets", help="List datasets in the catalogue.")
        dataset.add_argument("filter", nargs="*", help="Filter datasets with a list of key=value.", metavar="key=value")
        dataset.add_argument(
            "--json", help="Output as JSON (includes full records with locations)", action="store_true"
        )
        dataset.add_argument("--csv", dest="output_csv", help="Output locations as CSV", action="store_true")
        dataset.add_argument(
            "--locations",
            help="Show a table of all locations with name, platform, path, bytes and object count.",
            action="store_true",
        )

    #        tasks = sub_parser.add_parser("tasks")
    #        tasks.add_argument("filter", nargs="*")
    #        tasks.add_argument("-l", "--long", help="Details", action="store_true")
    #        tasks.add_argument("--sort", help="Sort by date", choices=["created", "updated"], default="updated")

    def run(self, args):
        if not args.subcommand:
            raise ValueError("Missing subcommand")

        getattr(self, f"run_{args.subcommand}", self._run_default)(args)

    def _run_default(self, args):
        collection = args.subcommand
        request = list_to_dict(args.filter)
        payload = RestItemList(collection).get(params=request)
        if args.json:
            print(json_pretty_dump(payload))
        else:
            for v in payload:
                print(v["name"])

    def run_datasets(self, args):
        import csv as csv_module
        import sys

        from anemoi.registry.entry.dataset import DatasetCatalogueEntry
        from anemoi.registry.rest import RestItem

        collection = args.subcommand
        request = list_to_dict(args.filter)
        payload = RestItemList(collection).get(params=request)

        needs_full_records = args.json or args.locations or args.output_csv
        if needs_full_records:
            records = [RestItem(collection, v["name"]).get() for v in payload]

        if args.json:
            print(json_pretty_dump(records))
        elif args.output_csv:
            writer = csv_module.writer(sys.stdout)
            writer.writerow(["name", "platform", "path", "bytes", "objects"])
            for record in records:
                writer.writerows(DatasetCatalogueEntry.location_rows(record))
        elif args.locations:
            rows = []
            for record in records:
                for name, platform, path, size, files in DatasetCatalogueEntry.location_rows(record):
                    rows.append(
                        (
                            name,
                            platform,
                            path,
                            bytes_to_human(size) if size is not None else "",
                            f"{files:,}" if files is not None else "",
                        )
                    )
            print(table(rows, ["Name", "Platform", "Path", "Bytes", "Objects"], ["<", "<", "<", ">", ">"]))
        else:
            for v in payload:
                print(v["name"])

    def run_weights(self, args):
        collection = args.subcommand
        request = list_to_dict(args.filter)
        payload = RestItemList(collection).get(params=request)
        if args.json:
            print(json_pretty_dump(payload))
        else:
            for v in payload:
                print(v["uuid"])

    def run_experiments(self, args):
        collection = args.subcommand
        request = list_to_dict(args.filter)
        payload = RestItemList(collection).get(params=request)
        if args.json:
            print(json_pretty_dump(payload))
        else:
            for v in payload:
                print(v["expver"])

    def run_tasks(self, args):
        collection = "tasks"
        request = list_to_dict(args.filter)
        data = RestItemList(collection).get(params=request)
        self.print_tasks(data, long=args.long, sort=args.sort)

    def print_tasks(self, data, long=False, sort="updated"):
        data = sorted(data, key=lambda x: x[sort])

        rows = []
        for v in data:
            if not isinstance(v, dict):
                raise ValueError(v)
            created = datetime.datetime.fromisoformat(v.pop("created"))
            updated = datetime.datetime.fromisoformat(v.pop("updated"))

            uuid = v.pop("uuid")
            content = " ".join(f"{k}={v}" for k, v in v.items())
            if not long:
                content = content[:20] + "..."
            rows.append(
                [
                    when(created),
                    when(updated),
                    v.pop("status"),
                    v.pop("progress", ""),
                    content,
                    uuid,
                ]
            )
        print(table(rows, ["Created", "Updated", "Status", "%", "Details", "UUID"], ["<", "<", "<", "<", "<", "<"]))
        return


command = List
