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
from anemoi.registry.tasks import TaskCatalogueEntry
from anemoi.registry.utils import list_to_dict
from anemoi.registry.workers import run_worker

LOG = logging.getLogger(__name__)


class WorkerCommand(BaseCommand):
    """Run a worker, taking ownership tasks, running them."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry

    collection = "tasks"

    def add_arguments(self, command_parser):

        subparsers = command_parser.add_subparsers(dest="action", help="Action to perform")

        transfer = subparsers.add_parser("transfer-dataset", help="Transfer dataset")
        transfer.add_argument(
            "--target-dir", help="The actual target directory where the worker will write.", default="."
        )
        transfer.add_argument("--published-target-dir", help="The target directory published in the catalogue.")
        transfer.add_argument("--destination", help="Platform destination (e.g. leonardo, lumi, marenostrum)")
        transfer.add_argument("--threads", help="Number of threads to use", type=int)
        transfer.add_argument("--filter-tasks", help="Filter tasks to process (key=value list)", nargs="*", default=[])

        delete = subparsers.add_parser("delete-dataset", help="Delete dataset")
        delete.add_argument("--platform", help="Platform destination (e.g. leonardo, lumi, marenostrum)")
        delete.add_argument("--filter-tasks", help="Filter tasks to process (key=value list)", nargs="*", default=[])

        dummy = subparsers.add_parser("dummy", help="Dummy worker for test purposes")
        dummy.add_argument("--arg")

        for subparser in [transfer, delete, dummy]:
            subparser.add_argument("--timeout", help="Die with timeout (SIGALARM) after TIMEOUT seconds.", type=int)
            subparser.add_argument("--wait", help="Check for new task every WAIT seconds.", type=int)
            subparser.add_argument("--heartbeat", help="Heartbeat interval", type=int)
            subparser.add_argument(
                "--max-no-heartbeat",
                help="Max interval without heartbeat before considering task needs to be freed.",
                type=int,
            )
            subparser.add_argument("--loop", help="Run in a loop", action="store_true")
            subparser.add_argument(
                "--check-todo",
                help="See if there are tasks for this worker and exit with 0 if there are task to do.",
                action="store_true",
            )
            subparser.add_argument("--dry-run", help="Dry run, do not actually do anything", action="store_true")

    def run(self, args):
        kwargs = vars(args)
        if "filter_tasks" in kwargs:
            kwargs["filter_tasks"] = list_to_dict(kwargs["filter_tasks"])
        kwargs.pop("command")
        kwargs.pop("debug")
        kwargs.pop("version")
        action = kwargs.pop("action")
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        run_worker(action, **kwargs)


command = WorkerCommand
