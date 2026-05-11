# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import importlib
import os

from anemoi.utils.cli import cli_main
from anemoi.utils.cli import make_parser

from . import __version__

_CLI_VERSION = os.environ.get("ANEMOI_REGISTRY_CLI_VERSION", "1")
_commands_module = importlib.import_module(f".v{_CLI_VERSION}.commands", "anemoi.registry")
COMMANDS = _commands_module.COMMANDS


# For read-the-docs
def create_parser():
    return make_parser(__doc__, COMMANDS)


def main():
    cli_main(__version__, __doc__, COMMANDS)


def main_PYTHON_ARGCOMPLETE_OK():
    # this is a workaround for argcomplete
    # to make sure the srting "PYTHON_ARGCOMPLETE_OK" is in the final executable script
    return main()


if __name__ == "__main__":
    main()
