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

from ..entry import CatalogueEntryNotFound
from . import Command

LOG = logging.getLogger(__name__)


class BaseCommand(Command):
    internal = True
    timestamp = True

    def check_arguments(self, args):
        pass

    def is_path(self, name_or_path):
        return os.path.exists(name_or_path)

    def is_identifier(self, name_or_path):
        try:
            self.entry_class(key=name_or_path)
            return True
        except CatalogueEntryNotFound:
            return False

    def run(self, args):
        args = vars(args)
        LOG.debug("anemoi-registry args:", args)
        if "command" in args:
            args.pop("command")
        name_or_path = args.pop("NAME_OR_PATH")

        if args.get("add_location"):
            args["add_location"] = self.parse_location(args["add_location"])
        if args.get("remove_location"):
            args["remove_location"] = self.parse_location(args["remove_location"])

        if self.is_path(name_or_path):
            LOG.info(f"Found local {self.kind} at {name_or_path}")
            self.run_from_path(name_or_path, **args)
            return

        if self.is_identifier(name_or_path):
            LOG.info(f"Processing {self.kind} with identifier '{name_or_path}'")
            self.run_from_identifier(name_or_path, **args)
            return

    def parse_location(self, location):
        for x in location:
            if "=" not in x:
                raise ValueError(f"Invalid location format '{x}', use 'key1=value1 key2=value2' list.")
        return {x.split("=")[0]: x.split("=")[1] for x in location}

    def warn_unused_arguments(self, kwargs):
        for k, v in kwargs.items():
            if v:
                LOG.warn(f"Ignoring argument {k}={v}")

    def run_from_identifier(self, *args, **kwargs):
        raise NotImplementedError()

    def run_from_path(self, *args, **kwargs):
        raise NotImplementedError()


command = BaseCommand
