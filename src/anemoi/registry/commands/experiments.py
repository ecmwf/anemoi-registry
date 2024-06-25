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

from ..entry import ExperimentCatalogueEntry
from ._base import BaseCommand

LOG = logging.getLogger(__name__)


class Experiments(BaseCommand):
    internal = True
    timestamp = True
    entry_class = ExperimentCatalogueEntry
    kind = "experiment"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME_OR_PATH", help=f"The name or the path of the {self.kind}")
        command_parser.add_argument("--register", help=f"Register the {self.kind}", action="store_true")
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting all)",
            action="store_true",
        )
        command_parser.add_argument("--json", help="Output json record", action="store_true")
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")

        command_parser.add_argument("--add-weights", nargs="+", help="Add weights to the experiment")
        command_parser.add_argument("--add-plots", nargs="+", help="Add plots to the experiment")
        command_parser.add_argument("--overwrite", help="Overwrite if already exists", action="store_true")

    def check_arguments(self, args):
        pass

    def is_path(self, name_or_path):
        if not os.path.exists(name_or_path):
            return False
        if not name_or_path.endswith(".yaml"):
            return False
        return True

    def run_from_identifier(
        self,
        identifier,
        json,
        add_weights,
        add_plots,
        unregister,
        overwrite,
        **kwargs,
    ):
        self.warn_unused_arguments(kwargs)

        entry = self.entry_class(key=identifier)

        if add_weights:
            for w in add_weights:
                entry.add_weights(w)
        if add_plots:
            for p in add_plots:
                entry.add_plots(p)

        if unregister:
            entry.unregister()

        # if delete:
        #    entry.delete()

        if json:
            print(entry.as_json())

    def run_from_path(
        self,
        path,
        register,
        unregister,
        add_weights,
        add_plots,
        overwrite,
        json,
        **kwargs,
    ):
        self.warn_unused_arguments(kwargs)

        entry = self.entry_class(path=path)

        if unregister:
            entry.unregister()
        if register:
            entry.register()
        if add_weights:
            for w in add_weights:
                entry.add_weights(w)
        if add_plots:
            for p in add_plots:
                entry.add_plots(p)

        # if delete:
        #    entry.delete()

        if json:
            print(entry.as_json())


command = Experiments
