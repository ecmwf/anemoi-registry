# (C) Copyright 2026 Anemoi contributors.
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
import signal
import sys
import threading
import time

from anemoi.utils.humanize import when

from .. import config
from ..tasks import TaskCatalogueEntry
from ..tasks import TaskCatalogueEntryList

# from anemoi.utils.provenance import trace_info

LOG = logging.getLogger(__name__)


class Worker:
    """Base class for a worker that processes tasks in the queue."""

    name = None

    DEFAULT_HEARTBEAT = 120
    DEFAULT_MAX_NO_HEARTBEAT = 600

    def __init__(
        self,
        heartbeat=DEFAULT_HEARTBEAT,
        max_no_heartbeat=DEFAULT_MAX_NO_HEARTBEAT,
        check_todo=False,
        timeout=None,
        timeout_exit_code=None,
        dry_run=False,
        **kwargs,
    ):
        """Run a worker that will process tasks in the queue.
        timeout: Kill itself after `timeout` seconds.
        """
        if kwargs:
            LOG.warning(f"Unknown arguments for Worker: {kwargs}")

        self.heartbeat = heartbeat
        self.max_no_heartbeat = max_no_heartbeat
        self.check_todo = check_todo
        self.dry_run = dry_run

        if timeout:

            def timeout_handler(signum, frame):
                # need to kill the process group to make sure all children are killed
                # especially when using multiprocessing/threads/Popens
                LOG.warning("Timeout reached, sending SIGHUP to the process group.")
                os.killpg(os.getpgrp(), signal.SIGHUP)

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

        self.filter_tasks = {"action": self.name}

    def run(self):

        if self.check_todo:
            # Check if there are tasks to do
            # exit with 0 if there are.
            # exit with 1 if there are none.
            task = self.choose_task()
            if task:
                LOG.info("There are tasks to do.")
                sys.exit(0)
            else:
                LOG.info("No tasks to do.")
                sys.exit(1)

        retries = 2
        for i in range(retries):
            try:
                self.process_one_task()
                break
            except Exception as e:
                LOG.error(f"Error : {e}")
                if i < retries - 1:
                    LOG.error("Retrying after this error.")
                else:
                    LOG.error("No more retries left.")
                    raise

    def process_one_task(self):
        task = self.choose_task()
        if not task:
            return

        uuid = task.key
        LOG.info(f"Processing task {uuid}: {task}")
        self.parse_task(task)  # for checking only

        self.take_ownership(task)
        try:
            self.process_task_with_heartbeat(task)
        except Exception as e:
            LOG.error(f"Error for task {task}: {e}")
            LOG.exception("Exception occurred during task processing:", exc_info=e)
            self.release_ownership(task)
            return
        LOG.info(f"Task {uuid} completed.")
        self.unregister(task)
        LOG.info(f"Task {uuid} deleted.")

    def process_task_with_heartbeat(self, task):
        STOP = []

        # create another thread to send heartbeat
        def send_heartbeat():
            while True:
                try:
                    self.set_status(task, "running")
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
            self.worker_process_task(task)
        finally:
            STOP.append(1)  # stop the heartbeat thread
            thread.join()

    @classmethod
    def parse_task(cls, task: TaskCatalogueEntry, *keys: list[str]):
        """Parse a task (from the catalogue) and return a list of values for the given keys."""
        data = task.record.copy()
        assert isinstance(data, dict), data

        def is_alphanumeric(s):
            assert isinstance(s, str), s
            return all(c.isalnum() or c in ("-", "_") for c in s)

        for k in keys:
            value = data.pop(k)
            assert is_alphanumeric(value), (k, value)
        for k in data:
            if k not in ("action", "status", "progress", "created", "updated", "uuid"):
                LOG.warning(f"Unknown key {k}=data[k]")
        return [task.record[k] for k in keys]

    def choose_task(self):
        for task in TaskCatalogueEntryList(status="queued", **self.filter_tasks):
            LOG.info("Found task")
            return task
        LOG.info(f"No queued tasks found with filter_tasks={self.filter_tasks}")

        if self.max_no_heartbeat == 0:
            return None

        cat = TaskCatalogueEntryList(status="running", **self.filter_tasks)
        if not cat:
            LOG.info("No queued tasks found")
        else:
            LOG.info(f"Tasks list \n{cat.to_str(long=True)}")

        # if a task is running, check if it has been running for too long, and free it
        for task in cat:
            updated = datetime.datetime.fromisoformat(task.record["updated"])
            LOG.info(f"Task {task.key} is already running, last update {when(updated, use_utc=True)}.")
            if (
                self.max_no_heartbeat >= 0
                and (datetime.datetime.utcnow() - updated).total_seconds() > self.max_no_heartbeat
            ):
                LOG.warning(
                    f"Task {task.key} has been running for more than {self.max_no_heartbeat} seconds, freeing it."
                )
                self.release_ownership(task)

    def take_ownership(self, task):
        if self.dry_run:
            LOG.warning(f"Would take ownership of task {task.key} but this is only a dry run.")
            return
        task.take_ownership()

    def release_ownership(self, task):
        if self.dry_run:
            LOG.warning(f"Would release ownership of task {task.key} but this is only a dry run.")
            return
        task.release_ownership()

    def unregister(self, task):
        if self.dry_run:
            LOG.warning(f"Would unregister task {task.key} but this is only a dry run.")
            return
        task.unregister()

    def set_status(self, task, status):
        if self.dry_run:
            LOG.warning(f"Would set status of task {task.key} to {status} but this is only a dry run.")
            return
        task.set_status(status)

    def worker_process_task(self, task):
        raise NotImplementedError("Subclasses must implement this method.")


def release_stalled(filters: dict = None, max_age: int = 600, force: bool = False, dry_run: bool = False) -> int:
    """Release ownership of running catalogue tasks whose heartbeat has stalled.

    Iterates over tasks currently in ``running`` status that match ``filters``,
    computes the age of each task's last ``updated`` heartbeat, and calls
    :py:meth:`TaskCatalogueEntry.release_ownership` on any whose heartbeat is
    older than ``max_age`` seconds. Intended to be called by the steward
    housekeeping job.

    Parameters
    ----------
    filters : dict, optional
        Catalogue filters (e.g. ``{"uuid": "..."}`` or ``{"action": "..."}``).
        When omitted, every running task is considered.
    max_age : int
        Heartbeat age in seconds above which a task is eligible for release.
    force : bool
        Release regardless of age.
    dry_run : bool
        Log the tasks that would be released without mutating the catalogue.

    Returns
    -------
    int
        The number of tasks actually released.
    """
    entries = TaskCatalogueEntryList(status="running", **(filters or {})).get()
    if not entries:
        LOG.info(f"No running tasks found matching {filters or {}}")
        return 0

    now = datetime.datetime.utcnow()
    released = 0
    for record in entries:
        uuid = record["uuid"]
        updated = datetime.datetime.fromisoformat(record["updated"])
        age = (now - updated).total_seconds()
        if not force and age < max_age:
            LOG.debug(f"Task {uuid}: heartbeat age {age:.0f}s < {max_age}s, skipping.")
            continue

        entry = TaskCatalogueEntry(key=uuid)
        if dry_run:
            LOG.warning(f"Would release task {uuid} (heartbeat age {age:.0f}s)")
            continue
        try:
            entry.release_ownership()
            LOG.info(f"Released task {uuid} (heartbeat age {age:.0f}s)")
            released += 1
        except Exception as e:
            LOG.error(f"Failed to release task {uuid}: {e}")

    LOG.info(f"Released {released} stalled task(s).")
    return released


def run_worker(action, **kwargs):
    from .delete_dataset import DeleteDatasetWorker
    from .dummy import DummyWorker
    from .monitor_datasets import MonitorDatasetsWorker
    from .monitor_storage import MonitorStorageWorker
    from .transfer_dataset import TransferDatasetWorker
    from .update_auxiliary import UpdateAuxiliaryWorker

    # Apply [worker] defaults from ~/.config/anemoi/steward.json
    try:
        from ..site.bootstrap import load_bootstrap

        bootstrap_worker = load_bootstrap().get("worker", {})
        for k, v in bootstrap_worker.items():
            if k not in kwargs:
                kwargs[k] = v
    except Exception:
        pass

    workers_config = config().get("workers", {})
    worker_config = workers_config.get(action, {})

    LOG.debug(kwargs)

    for k, v in worker_config.items():
        if k not in kwargs:
            kwargs[k] = v

    LOG.debug(kwargs)

    for k, v in workers_config.items():
        if isinstance(v, dict):
            continue
        if k not in kwargs:
            kwargs[k] = v

    LOG.info(f"Running worker {action} with kwargs {kwargs}")

    cls = {
        "transfer-dataset": TransferDatasetWorker,
        "delete-dataset": DeleteDatasetWorker,
        "monitor-storage": MonitorStorageWorker,
        "monitor-datasets": MonitorDatasetsWorker,
        "update-auxiliary": UpdateAuxiliaryWorker,
        "dummy": DummyWorker,
    }[action]
    cls(**kwargs).run()
