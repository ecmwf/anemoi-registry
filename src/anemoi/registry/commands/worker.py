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
from anemoi.registry.workers import TransferDatasetWorker

LOG = logging.getLogger(__name__)


class WorkerCommand(BaseCommand):
    """Run a worker, taking ownership tasks, running them."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry

    collection = "tasks"

    def add_arguments(self, command_parser):
        command_parser.add_argument("--timeout", help="Die with timeout (SIGALARM) after TIMEOUT seconds.", type=int)
        command_parser.add_argument("--wait", help="Check for new task every WAIT seconds.", type=int, default=60)

        command_parser.add_argument(
            "action",
            help="Action to perform",
            choices=["transfer-dataset", "delete-dataset"],
            nargs="?",
        )
        command_parser.add_argument(
            "--target-dir", help="The actual target directory where the worker will write.", default="."
        )
        command_parser.add_argument("--published-target-dir", help="The target directory published in the catalogue.")
        command_parser.add_argument("--destination", help="Platform destination (e.g. leonardo, lumi, marenostrum)")
        command_parser.add_argument("--request", help="Filter tasks to process (key=value list)", nargs="*", default=[])
        command_parser.add_argument("--threads", help="Number of threads to use", type=int, default=1)
        command_parser.add_argument("--heartbeat", help="Heartbeat interval", type=int, default=60)
        command_parser.add_argument(
            "--max-no-heartbeat",
            help="Max interval without heartbeat before considering task needs to be freed.",
            type=int,
            default=0,
        )
        command_parser.add_argument("--loop", help="Run in a loop", action="store_true")
        command_parser.add_argument(
            "--check-todo",
            help="See if there are tasks for this worker and exit with 0 if there are task to do.",
            action="store_true",
        )

    def run(self, args):
        kwargs = vars(args)
        kwargs["request"] = list_to_dict(kwargs["request"])
        kwargs.pop("command")
        kwargs.pop("debug")
        kwargs.pop("version")

        TransferDatasetWorker(**kwargs).run()


command = WorkerCommand
