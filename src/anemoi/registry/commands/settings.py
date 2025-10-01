# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import argparse
import logging

import yaml

from anemoi.registry import config

LOG = logging.getLogger(__name__)


class Settings:
    """Show current settings and quit. For debug purposes only."""

    internal = True
    timestamp = True

    def check(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """Check the command arguments."""
        pass

    def add_arguments(self, command_parser):
        command_parser.add_argument("--show-secrets", help="Show the token in the output", action="store_true")

    def run(self, args):
        from anemoi.utils.config import DotDict

        d = config(with_secrets=args.show_secrets)

        def convert_dict(d):
            if isinstance(d, DotDict):
                d = {k: convert_dict(v) for k, v in d.items()}
            return d

        d = convert_dict(d)
        print("anemoi-registry settings:")
        print("-------------------------")
        print(yaml.dump(d, indent=2, sort_keys=False))


command = Settings
