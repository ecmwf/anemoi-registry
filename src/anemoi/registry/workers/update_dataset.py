# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import datetime
import logging
import os
from copy import deepcopy

from anemoi.registry.entry.dataset import DatasetCatalogueEntry

from . import Worker

LOG = logging.getLogger(__name__)


class Progress:
    latest = None

    def __init__(self, task, frequency=60):
        self.task = task
        self.frequency = frequency
        self.first_progress = None
        self.first_transfer_progress = None
        self.previous_progress = None

    def __call__(self, number_of_files, total_size, total_transferred, transfering, **kwargs):
        now = datetime.datetime.utcnow()

        if self.latest is not None and (now - self.latest).seconds < self.frequency:
            # already updated recently
            return
        self.latest = now

        timestamp = now.isoformat()

        progress = dict(
            number_of_files=number_of_files,
            total_size=total_size,
            total_transferred=total_transferred,
            transfering=transfering,
            timestamp=timestamp,
            percentage=100 * total_transferred / total_size if total_size and transfering else 0,
            **kwargs,
        )

        if self.first_progress is None:
            self.first_progress = progress
        if self.first_transfer_progress is None and transfering:
            self.first_transfer_progress = progress

        p = deepcopy(progress)
        p["first_progress"] = self.first_progress
        p["first_transfer_progress"] = self.first_transfer_progress
        p["previous_progress"] = self.previous_progress
        self.task.set_progress(p)

        self.previous_progress = progress


class UpdateDatasetWorker(Worker):
    """Patch datsets from the catalogue"""

    name = "update-dataset"

    def __init__(
        self,
        destination,
        directory=None,
        filter_tasks={},
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.destination = destination
        self.directory = directory
        if not self.destination:
            raise ValueError("No destination platform specified")

        if not self.directory:
            # in this case should get the directory from the catalogue
            raise NotImplementedError("No directory specified")

        if self.directory:
            if not os.path.exists(self.directory):
                raise ValueError(f"Directory {self.directory} does not exist")

        self.filter_tasks.update(filter_tasks)
        self.filter_tasks["destination"] = self.destination

    def worker_process_task(self, task):
        from anemoi.registry.commands.update import zarr_file_from_catalogue

        (destination,) = self.parse_task(task)
        assert destination == self.destination, (destination, self.destination)

        for path in os.listdir(self.directory):
            path = os.path.join(self.directory, path)
            if not path.endswith(".zarr"):
                continue
            name = os.path.basename(path)[:-5]

            LOG.info(f"Updating dataset '{name}' from catalogue on '{destination}'")

            def check_path(name, path):
                entry = DatasetCatalogueEntry(key=name)
                locations = entry.record["locations"]
                if destination not in locations:
                    raise ValueError(
                        f"Platform '{destination}' not registerd as a location in the catalogue. Not updating."
                    )
                catalogue_path = locations[self.destination]["path"]
                if os.path.realpath(path) != os.path.realpath(catalogue_path):
                    raise ValueError(f"Path '{path}' does not match catalogue path {catalogue_path}. Not updating.")

            try:
                check_path(name, path)
                zarr_file_from_catalogue(path, dry_run=False, ignore=False, _error=print)
            except Exception as e:
                LOG.error(f"Error updating {path}: {e}")
                continue

    @classmethod
    def parse_task(cls, task):
        assert task.record["action"] == "update-dataset", task.record["action"]

        destination = super().parse_task(task, "destination")

        if "/" in destination:
            raise ValueError(f"Destination '{destination}' must not contain '/', this is a platform name")
        if "." in destination:
            raise ValueError(f"Destination '{destination}' must not contain '.', this is a platform name")

        return destination
