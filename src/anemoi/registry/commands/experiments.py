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
import os

from ..entry.experiment import ExperimentCatalogueEntry
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class Experiments(BaseCommand):
    """Manage experiments in the catalogue. Register, unregister, add weights, add plots, etc."""

    internal = True
    timestamp = True
    entry_class = ExperimentCatalogueEntry
    kind = "experiment"

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "NAME_OR_PATH", help="Name of an experiment of a path of an experiment config file."
        )
        command_parser.add_argument(
            "--register", help=f"Register the {self.kind} in the catalogue.", action="store_true"
        )
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting the experiment from other locations)",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")

        command_parser.add_argument("--add-weights", nargs="+", help="Add weights to the experiment.")
        command_parser.add_argument("--add-plots", nargs="+", help="Add plots to the experiment.")
        command_parser.add_argument("--add-artefacts", nargs="+", help="Add artefacts to the experiment.")
        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")

    def check_arguments(self, args):
        pass

    def is_path(self, name_or_path):
        if not os.path.exists(name_or_path):
            return False
        if not name_or_path.endswith(".yaml"):
            return False
        return True

    def _run(self, entry, args):
        self.process_task(entry, args, "unregister")
        self.process_task(entry, args, "register", overwrite=args.overwrite)
        self.process_task(entry, args, "add_weights")
        self.process_task(entry, args, "add_artefacts")
        self.process_task(entry, args, "add_plots")


command = Experiments