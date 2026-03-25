# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site management command: setup, monitoring, and auxiliary file downloads."""

import logging

from . import Command

LOG = logging.getLogger(__name__)

WORKFLOW = """
Workflow:
  1. Setup (once, runs check + fetches configs):
     %(prog)s --setup https://server/api/v1/sites/<site>

  2. Run monitoring (e.g., cron job):
     %(prog)s --storage     # report quota usage
     %(prog)s --datasets    # report dataset replica status
     %(prog)s --all         # both

  Optional:
     %(prog)s --update-auxiliary   # download auxiliary files
     %(prog)s --dry-run            # test without sending data
"""


class Site(Command):
    """Site agent: setup, monitor quota/replicas, download auxiliary files."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "--setup",
            metavar="URL",
            help="Set up bootstrap, check server, and fetch configs",
        )
        command_parser.add_argument(
            "--update-auxiliary",
            action="store_true",
            help="Download auxiliary files from remote storage",
        )
        command_parser.add_argument(
            "--storage",
            action="store_true",
            help="Report quota/storage usage",
        )
        command_parser.add_argument(
            "--datasets",
            action="store_true",
            help="Report dataset replica status",
        )
        command_parser.add_argument(
            "--all",
            action="store_true",
            help="Run both --storage and --datasets",
        )
        command_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be sent without sending",
        )

        command_parser.epilog = WORKFLOW

    def run(self, args):
        from ..entry.site import SiteCatalogueEntry

        site = SiteCatalogueEntry(name="local")

        if args.setup:
            site.setup(args.setup)
            return

        if args.update_auxiliary:
            site.update_auxiliary(dry_run=args.dry_run)

        if args.storage or args.all:
            site.report_storage(dry_run=args.dry_run)

        if args.datasets or args.all:
            site.report_datasets(dry_run=args.dry_run)


command = Site
