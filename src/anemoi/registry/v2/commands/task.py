# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..entry import CatalogueEntryNotFound
from ..tasks import TaskCatalogueEntry
from ..tasks import TaskCatalogueEntryList
from ..utils import list_to_dict
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Tasks(BaseCommand):
    """Admin tool. Manage tasks in the catalogue."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry

    collection = "tasks"

    def add_arguments(self, command_parser):
        command_parser.add_argument("TASK", help="The uuid of the task", nargs="?")

        group = command_parser.add_mutually_exclusive_group()
        group.add_argument("--register", help="Add a new queue entry", nargs="*", metavar="K=V")
        group.add_argument(
            "--unregister", help="Remove task by TASK uuid, or matching K=V filters", nargs="*", metavar="K=V"
        )
        group.add_argument("--list", help="List tasks matching K=V filters", nargs="*", metavar="K=V")

        command_parser.add_argument("--list-sort", help="Sort field for --list.", default="updated")
        command_parser.add_argument(
            "--list-fields",
            help="Comma-separated field names to display with --list.",
            type=lambda s: [f.strip() for f in s.split(",")],
            metavar="FIELDS",
        )
        command_parser.add_argument(
            "--list-format",
            help="Output format for --list.",
            choices=["text", "csv", "json", "rich"],
            default="rich",
        )
        command_parser.add_argument("-l", "--long", help="Long output for --list.", action="store_true")
        command_parser.add_argument("-y", "--yes", help="Assume yes for --unregister.", action="store_true")

    def run(self, args):
        if args.TASK is not None and (args.register is not None or args.list is not None):
            raise ValueError("Cannot use positional argument TASK with --register or --list")

        if args.unregister is not None and args.TASK:
            self.entry_class(key=args.TASK).unregister()
            return

        if args.TASK:
            return self.run_with_uuid(args.TASK, args)
        if args.register is not None:
            self.run_new(args)
        if args.list is not None:
            self.run_list(args)
        if args.unregister is not None:
            self.run_delete_many(args)

    def run_with_uuid(self, uuid, args):
        pass

    def run_new(self, args):
        cat = TaskCatalogueEntryList()
        new = list_to_dict(args.register)
        uuid = cat.add_new_task(**new)
        print(uuid)

    def run_list(self, args):
        fmt = args.list_format
        fields = args.list_fields
        filters = list_to_dict(args.list) if args.list else {}

        if fmt == "text" and not fields:
            # Legacy mode: use the built-in to_str formatting
            cat = TaskCatalogueEntryList(**filters, sort=args.list_sort)
            print(cat.to_str(args.long))
            return

        from .base import format_list_output

        cat = TaskCatalogueEntryList(**filters, sort=args.list_sort)
        rows = list(cat.get())
        if not fields:
            fields = ["uuid", "action", "status", "created", "updated"]
        elif "*" in fields:
            all_keys = dict.fromkeys(k for row in rows for k in row)
            fields = [f for f in fields if f != "*"] + [k for k in all_keys if k not in fields]
        format_list_output(rows, fields, fmt)

    def run_delete_many(self, args):
        if not args.unregister:
            raise ValueError("--unregister without a TASK requires K=V filters to avoid deleting everything.")
        filters = list_to_dict(args.unregister)
        cat = TaskCatalogueEntryList(**filters, sort=args.list_sort)
        if not cat:
            LOG.info("No tasks found")
            return
        if not args.yes:
            print(f"Do you really want to delete these {len(cat)} entries? (y/n)", end=" ")
            if input("").lower() != "y":
                return
        count = 0
        while cat:
            try:
                entry = cat[0]
                entry.unregister()
                count += 1
                LOG.info(f"Task {entry.key} deleted.")
            except CatalogueEntryNotFound:
                LOG.warning(f"Task {entry.key} not found.")
        LOG.info(f"{count} tasks deleted.")


command = Tasks
