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

from ..entry import WeightCatalogueEntry
from ._base import BaseCommand

LOG = logging.getLogger(__name__)


class Weights(BaseCommand):
    internal = True
    timestamp = True
    entry_class = WeightCatalogueEntry
    kind = "weights"

    def add_arguments(self, command_parser):
        command_parser.add_argument("NAME_OR_PATH", help=f"The name or the path of the {self.kind}")
        command_parser.add_argument("--register", help=f"Register the {self.kind}", action="store_true")
        command_parser.add_argument(
            "--unregister",
            help="Remove from catalogue (without deleting all)",
            action="store_true",
        )
        # command_parser.add_argument("--delete", help=f"Delete the {self.kind} from the catalogue and from any other location", action="store_true")
        command_parser.add_argument("--json", help="Output json record", action="store_true")

        command_parser.add_argument("--add-location", nargs="+", help="Add a location to the weights")

        command_parser.add_argument("--overwrite", help="Overwrite any existing weights", action="store_true")

    def check_arguments(self, args):
        pass

    def parse_location(self, location):
        for x in location:
            if "=" not in x:
                raise ValueError(f"Invalid location format '{x}', use 'key1=value1 key2=value2' list.")
        return {x.split("=")[0]: x.split("=")[1] for x in location}

    def warn_unused_arguments(self, kwargs):
        for k, v in kwargs.items():
            if v:
                LOG.info(f"Ignoring argument {k}={v}")

    def run_from_identifier(
        self,
        identifier,
        add_location,
        json,
        unregister,
        remove_location=False,
        **kwargs,
    ):
        self.warn_unused_arguments(kwargs)

        entry = self.entry_class(key=identifier)

        if add_location:
            entry.add_location(**add_location)
        if remove_location:
            entry.remove_location(**remove_location)
        if unregister:
            entry.unregister()

        if json:
            print(entry.as_json())

    def run_from_path(
        self,
        path,
        unregister,
        register,
        add_location,
        overwrite,
        json,
        remove_location=False,
        **kwargs,
    ):
        self.warn_unused_arguments(kwargs)

        entry = self.entry_class(path=path)

        if unregister:
            entry.unregister()
        if register:
            entry.register(overwrite=overwrite)

        if add_location:
            entry.add_location(**add_location)
        # if remove_location:
        #    entry.remove_location(**remove_location)
        # if delete:
        #    entry.delete()

        if json:
            print(entry.as_json())


command = Weights
