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

LOG = logging.getLogger(__name__)


class Download:
    """Just download."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument("path", help="Path to download.")
        command_parser.add_argument("target", help="Target path.", nargs="?", default=None)
        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")

    def run(self, args):
        from anemoi.utils.s3 import download

        target = args.target

        if target is None:
            target = os.path.basename(args.path)
        download(args.path, target, overwrite=args.overwrite)


command = Download
