# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging
import os
import signal
import sys
import threading
import time

from anemoi.utils.humanize import when

from anemoi.registry.entry.dataset import DatasetCatalogueEntry
from anemoi.registry.tasks import TaskCatalogueEntryList

# from anemoi.utils.provenance import trace_info

LOG = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        action,
        destination,
        timeout=None,
        wait=60,
        stop_if_finished=True,
        target_dir=".",
        published_target_dir=None,
        auto_register=True,
        threads=1,
        heartbeat=60,
        max_no_heartbeat=0,
        loop=False,
        check_todo=False,
        request={},
    ):
        """Run a worker that will process tasks in the queue.
        timeout: Kill itself after `timeout` seconds.
        wait: When no task is found, wait `wait` seconds before checking again.
        """
        assert action == "transfer-dataset", action

        if not destination:
            raise ValueError("No destination platform specified")
        if not action:
            raise ValueError("No action specified")

        self.destination = destination
        self.target_dir = target_dir
        self.published_target_dir = published_target_dir or target_dir
        self.request = request
        self.threads = threads
        self.heartbeat = heartbeat
        self.max_no_heartbeat = max_no_heartbeat
        self.loop = loop
        self.check_todo = check_todo

        self.wait = wait
        self.stop_if_finished = stop_if_finished
        self.auto_register = auto_register
        if timeout:
            signal.alarm(timeout)

        if not os.path.exists(target_dir):
            raise ValueError(f"Target directory {target_dir} must already exist")

    def run(self):
        if self.check_todo:
            task = self.choose_task()
            if task:
                LOG.info("There are tasks to do.")
                sys.exit(0)
            else:
                LOG.info("No tasks to do.")
                sys.exit(1)

        if self.loop:
            while True:
                res = self.process_one_task()

                if self.stop_if_finished and res is None:
                    LOG.info("All tasks have been processed, stopping.")
                    return

                LOG.info(f"Waiting {self.wait} seconds before checking again.")
                time.sleep(self.wait)
        else:
            self.process_one_task()

    def choose_task(self):
        request = self.request.copy()
        request["destination"] = request.get("destination", self.destination)
        request["action"] = "transfer-dataset"

        # if a task is queued, take it
        for entry in TaskCatalogueEntryList(status="queued", **request):
            return entry

        # else if a task is running, check if it has been running for too long, and free it
        if self.max_no_heartbeat == 0:
            return None

        cat = TaskCatalogueEntryList(status="running", **request)
        if not cat:
            LOG.info("No queued tasks found")
        else:
            LOG.info(cat.to_str(long=True))
        for entry in cat:
            updated = datetime.datetime.fromisoformat(entry.record["updated"])
            LOG.info(f"Task {entry.key} is already running, last update {when(updated, use_utc=True)}.")
            if (datetime.datetime.utcnow() - updated).total_seconds() > self.max_no_heartbeat:
                LOG.warning(
                    f"Task {entry.key} has been running for more than {self.max_no_heartbeat} seconds, freeing it."
                )
                entry.release_ownership()

    def process_one_task(self):
        entry = self.choose_task()
        if not entry:
            return False

        uuid = entry.key
        LOG.info(f"Processing task {uuid}: {entry}")
        self.parse_entry(entry)  # for checking only

        entry.take_ownership()
        self.process_entry_with_heartbeat(entry)
        LOG.info(f"Task {uuid} completed.")
        entry.unregister()
        LOG.info(f"Task {uuid} deleted.")
        return True

    def process_entry_with_heartbeat(self, entry):
        STOP = []

        # create another thread to send heartbeat
        def send_heartbeat():
            while True:
                try:
                    entry.set_status("running")
                except Exception:
                    return
                for _ in range(self.heartbeat):
                    time.sleep(1)
                    if len(STOP) > 0:
                        STOP.pop()
                        return

        thread = threading.Thread(target=send_heartbeat)
        thread.start()

        try:
            self.process_entry(entry)
        finally:
            STOP.append(1)  # stop the heartbeat thread
            thread.join()

    def process_entry(self, entry):
        destination, source, dataset = self.parse_entry(entry)
        dataset_entry = DatasetCatalogueEntry(key=dataset)

        LOG.info(f"Transferring {dataset} from '{source}' to '{destination}'")

        def get_source_path():
            e = dataset_entry.record
            if "locations" not in e:
                raise ValueError(f"Dataset {dataset} has no locations")
            locations = e["locations"]

            if source not in locations:
                raise ValueError(
                    f"Dataset {dataset} is not available at {source}. Available locations: {list(locations.keys())}"
                )

            if "path" not in locations[source]:
                raise ValueError(f"Dataset {dataset} has no path at {source}")

            path = locations[source]["path"]

            return path

        source_path = get_source_path()
        basename = os.path.basename(source_path)
        target_path = os.path.join(self.target_dir, basename)
        if os.path.exists(target_path):
            LOG.error(f"Target path {target_path} already exists, skipping.")
            return

        from anemoi.utils.s3 import download

        LOG.info(f"Source path: {source_path}")
        LOG.info(f"Target path: {target_path}")

        if source_path.startswith("s3://"):
            source_path = source_path + "/" if not source_path.endswith("/") else source_path

        if target_path.startswith("s3://"):
            # untested
            download(source_path, target_path, resume=True, threads=self.threads)
            return
        else:
            target_tmp_path = os.path.join(self.target_dir + "-downloading", basename)
            os.makedirs(os.path.dirname(target_tmp_path), exist_ok=True)
            download(source_path, target_tmp_path, resume=True, threads=self.threads)
            os.rename(target_tmp_path, target_path)

        if self.auto_register:
            published_target_path = os.path.join(self.published_target_dir, basename)
            dataset_entry.add_location(platform=destination, path=published_target_path)

    @classmethod
    def parse_entry(cls, entry):
        data = entry.record.copy()

        assert isinstance(data, dict), data
        assert data["action"] == "transfer-dataset", data["action"]

        def is_alphanumeric(s):
            assert isinstance(s, str), s
            return all(c.isalnum() or c in ("-", "_") for c in s)

        destination = data.pop("destination")
        source = data.pop("source")
        dataset = data.pop("dataset")
        assert is_alphanumeric(destination), destination
        assert is_alphanumeric(source), source
        assert is_alphanumeric(dataset), dataset
        for k in data:
            if k not in ("action", "status", "progress", "created", "updated", "uuid"):
                LOG.warning(f"Unknown key {k}=data[k]")
        data = None

        if "/" in destination:
            raise ValueError(f"Destination {destination} must not contain '/', this is a platform name")
        if "." in destination:
            raise ValueError(f"Destination {destination} must not contain '.', this is a platform name")

        if "/" in source:
            raise ValueError(f"Source {source} must not contain '/', this is a platform name")
        if "." in source:
            raise ValueError(f"Source {source} must not contain '.', this is a platform name")

        if "." in dataset:
            raise ValueError(f"The dataset {dataset} must not contain a '.', this is the name of the dataset.")

        assert isinstance(destination, str), destination
        assert isinstance(source, str), source
        assert isinstance(dataset, str), dataset
        return destination, source, dataset
