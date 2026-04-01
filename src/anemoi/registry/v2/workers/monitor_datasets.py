# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging

from . import Worker

LOG = logging.getLogger(__name__)


class MonitorDatasetsWorker(Worker):
    """Worker that reports dataset replica status for the local site."""

    name = "monitor-datasets"

    def __init__(self, dry_run=False, **kwargs):
        super().__init__(dry_run=dry_run, **kwargs)
        self.dry_run = dry_run

    def worker_process_task(self, task):
        from ..entry.site import SiteCatalogueEntry

        SiteCatalogueEntry(name="local").report_datasets(dry_run=self.dry_run)
