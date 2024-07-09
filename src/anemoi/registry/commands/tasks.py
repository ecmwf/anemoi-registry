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

from anemoi.registry.commands.base import BaseCommand
from anemoi.registry.entry import CatalogueEntryNotFound
from anemoi.registry.tasks import TaskCatalogueEntry
from anemoi.registry.tasks import TaskCatalogueEntryList
from anemoi.registry.utils import list_to_dict

LOG = logging.getLogger(__name__)


class Tasks(BaseCommand):
    """Admin tool. Manage tasks in the catalogue."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry

    collection = "tasks"

    def add_arguments(self, command_parser):
        command_parser.add_argument("TASK", help="The uuid of the task", nargs="?")
        command_parser.add_argument("--set-status", help="Set status of the given task", metavar="STATUS")
        command_parser.add_argument(
            "--set-progress", help="Set progress of the given task (0 to 100 percents)", type=int, metavar="N"
        )
        command_parser.add_argument("--own", help="Take ownership of a task", action="store_true")
        command_parser.add_argument("--disown", help="Release a task and requeue it", action="store_true")

        group = command_parser.add_mutually_exclusive_group()
        group.add_argument("--new", help="Add a new queue entry", nargs="*", metavar="K=V")
        group.add_argument(
            "--take-one", help="Take ownership of the oldest entry with status=queued", nargs="*", metavar="K=V"
        )
        group.add_argument("--list", help="List tasks", nargs="*", metavar="K=V")
        group.add_argument("--delete-many", help="Batch remove multiple tasks", nargs="*", metavar="K=V")

        command_parser.add_argument(
            "--sort",
            help="Sort by date. Use with --list, --take-one",
            choices=["created", "updated"],
            default="updated",
        )
        command_parser.add_argument("-l", "--long", help="Details, use with --list", action="store_true")
        command_parser.add_argument("-y", "--yes", help="Assume yes", action="store_true")

    def run(self, args):
        if args.TASK is not None and (args.new is not None or args.take_one is not None or args.list is not None):
            raise ValueError("Cannot use positional argument TASK with --new, --take-one or --list")

        if args.TASK:
            return self.run_with_uuid(args.TASK, args)
        if args.new is not None:
            self.run_new(args)
        if args.take_one is not None:
            self.run_take_one(args)
        if args.list is not None:
            self.run_list(args)
        if args.delete_many is not None:
            assert args.TASK is None
            self.run_delete_many(args)

    def run_with_uuid(self, uuid, args):

        uuid = args.TASK
        entry = self.entry_class(key=uuid)

        self.process_task(entry, args, "disown", "release_ownership")
        self.process_task(entry, args, "own", "take_ownership")
        self.process_task(entry, args, "set_status")
        self.process_task(entry, args, "set_progress")

    def run_new(self, args):
        cat = TaskCatalogueEntryList()
        new = list_to_dict(args.new)
        uuid = cat.add_new_task(**new)
        print(uuid)

    def run_list(self, args):
        cat = TaskCatalogueEntryList(*args.list, sort=args.sort)
        print(cat.to_str(args.long))

    def run_delete_many(self, args):
        cat = TaskCatalogueEntryList(*args.delete_many, sort=args.sort)
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

    def run_take_one(self, args):
        cat = TaskCatalogueEntryList(*args.take_one, status="queued", sort=args.sort)
        uuid = cat.take_last()
        if uuid is None:
            return
        else:
            print(uuid)


command = Tasks
