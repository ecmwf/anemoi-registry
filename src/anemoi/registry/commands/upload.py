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

UPLOAD_ALLOWED = False
if os.environ.get("ANEMOI_FORCE_UPLOAD"):
    UPLOAD_ALLOWED = True


class Upload:
    """Just upload."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument("path", help="Path to upload.")
        command_parser.add_argument(
            "target",
            help="Target s3 path. Please consider using `anemoi-registry experiment <expver> --add-artefacts path`",
        )
        command_parser.add_argument("--overwrite", help="Overwrite if already exists.", action="store_true")

    def run(self, args):
        if not UPLOAD_ALLOWED:
            LOG.error("Direct upload not allowed.")
            return
        from anemoi.utils.s3 import upload

        upload(args.path, args.target, overwrite=args.overwrite)


command = Upload
