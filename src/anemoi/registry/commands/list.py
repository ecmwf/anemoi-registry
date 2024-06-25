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

import json
import logging

from anemoi.registry.rest import ReadOnlyRest as Rest

from . import Command

LOG = logging.getLogger(__name__)


class List(Command):
    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        sub_parser = command_parser.add_subparsers(dest="subcommand")

        experiment = sub_parser.add_parser("experiments")  # noqa: F841
        checkpoint = sub_parser.add_parser("weights")  # noqa: F841
        dataset = sub_parser.add_parser("datasets")  # noqa: F841

    def check_arguments(self, args):
        pass

    def run(self, args):
        if not args.subcommand:
            raise ValueError("Missing subcommand")

        subcommand = f"run_{args.subcommand.replace('-', '_')}"
        return getattr(self, subcommand)(args)

    def run_experiments(self, args):
        payload = Rest().get("experiments")
        print(json.dumps(payload, indent=2))

    def run_weights(self, args):
        payload = Rest().get("weights")
        print(json.dumps(payload, indent=2))

    def run_datasets(self, args):
        payload = Rest().get("datasets")
        print(json.dumps(payload, indent=2))


command = List
