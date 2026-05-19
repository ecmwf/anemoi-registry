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
from typing import Any

from anemoi.utils.humanize import when
from anemoi.utils.text import table

from .entry import CatalogueEntry
from .rest import RestItemList
from .rest import trace_info
from .utils import list_to_dict

LOG = logging.getLogger(__name__)


class TaskNotQueuedError(RuntimeError):
    """Raised when take_ownership() fails because the task is not in 'queued' state."""


class NoTaskAvailable(RuntimeError):
    """Raised when no task matching the given filter is available to be picked up."""


class TaskCatalogueEntryList:
    """List of task catalogue entries."""

    collection = "tasks"
    main_key = "uuid"

    def __init__(self, *args, sort="updated", **kwargs):
        if args:
            for k, v in list_to_dict(args).items():
                if k in kwargs:
                    raise ValueError(f"Duplicate argument {k}={v} and {k}={kwargs[k]}")
                kwargs[k] = v
        self.kwargs = kwargs
        self.sort = sort

    @classmethod
    def rest_collection(cls):
        return RestItemList(cls.collection)

    def get(self):
        data = self.rest_collection().get(params=self.kwargs)
        return sorted(data, key=lambda x: x[self.sort])

    def __iter__(self):
        for v in self.get():
            yield TaskCatalogueEntry(key=v["uuid"])

    def __getitem__(self, key):
        return list(self)[key]

    def __len__(self):
        return len(self.get())

    def add_new_task(self, **kwargs):
        kwargs = kwargs.copy()
        assert "action" in kwargs, kwargs
        kwargs["action"] = kwargs["action"].replace("_", "-").lower()

        res = self.rest_collection().post(kwargs)
        uuid = res["uuid"]
        LOG.debug(f"New task created {uuid}: {res}")
        return uuid

    def take_last(self):
        uuids = [v["uuid"] for v in self.get()]
        if not uuids:
            LOG.info("No available task has been found.")
            return
        latest = uuids[-1]

        entry = TaskCatalogueEntry(key=latest)
        res = entry.take_ownership()
        LOG.debug(f"Task {latest} taken: {res}")
        return res["uuid"]

    @classmethod
    def get_latest(
        cls,
        select: dict[str, Any],
        steal_if_stale_after_seconds: int | None = None,
        status: str = "queued",
        stealable_status: str = "running",
    ) -> "TaskCatalogueEntry":
        """Pick the oldest-updated task matching ``select``.

        Prefers tasks in ``status``. If none are found and
        ``steal_if_stale_after_seconds`` is set, falls back to tasks in
        ``stealable_status`` whose last update is older than that threshold
        (assumed to belong to a dead worker that ``take_ownership`` can reclaim).

        Parameters
        ----------
        select : dict
            Filter criteria forwarded as query parameters, e.g.
            ``{"action": "transfer-dataset", "destination": "ewc"}``.
            Must not contain a ``status`` key.
        steal_if_stale_after_seconds : int, optional
            If set, fall back to ``stealable_status`` tasks whose last update
            is older than this many seconds when no ``status`` task is found.
        status : str, optional
            Primary status to look for. Default ``"queued"``.
        stealable_status : str, optional
            Fallback status to consider stealable when stale. Default ``"running"``.

        Returns
        -------
        TaskCatalogueEntry
            The oldest-updated task matching the criteria.

        Raises
        ------
        NoTaskAvailable
            If no matching task is available.
        """
        primary = list(cls(**select, status=status))
        if primary:
            return primary[0]

        if steal_if_stale_after_seconds is None:
            raise NoTaskAvailable(f"No {status!r} task matching {select}")

        now = datetime.datetime.now()
        for task in cls(**select, status=stealable_status):
            updated = datetime.datetime.fromisoformat(task.record["updated"])
            age = (now - updated).total_seconds()
            if age > steal_if_stale_after_seconds:
                LOG.warning(
                    "Task %s appears stale (last update %.0fs ago > %ds threshold)",
                    task.key, age, steal_if_stale_after_seconds,
                )
                return task

        raise NoTaskAvailable(
            f"No {status!r} (or stale {stealable_status!r}) task matching {select}"
        )

    def to_str(self, long):
        rows = []
        for v in self.get():
            if not isinstance(v, dict):
                raise ValueError(v)
            created = datetime.datetime.fromisoformat(v.pop("created"))
            updated = datetime.datetime.fromisoformat(v.pop("updated"))

            uuid = v.pop("uuid")
            status = v.pop("status")
            progress = v.pop("progress", {}).get("percentage", "")
            action = v.pop("action", "")
            source = v.pop("source", "")
            destination = v.pop("destination", "")
            dataset = v.pop("dataset", "")
            row = [
                when(created, use_utc=True),
                when(updated, use_utc=True),
                status,
                action,
                source,
                destination,
                dataset,
                progress,
                uuid,
            ]
            rows.append(row)
            if long:
                content = " ".join(f"{k}={v}" for k, v in v.items())
                row.append(content)
        cols = ["Created", "Updated", "Status", "Action", "Src", "Dest", "Dataset", "%", "UUID"]
        if long:
            cols.append("More")

        return table(rows, cols, "<" * len(cols))


class TaskCatalogueEntry(CatalogueEntry):
    collection = "tasks"
    main_key = "uuid"

    def __repr__(self):
        r = self.record or {}
        parts = []
        for field in ("action", "status"):
            v = r.get(field)
            if v is not None:
                parts.append(f"{field}={v}")
        src, dst = r.get("source"), r.get("destination")
        if src is not None or dst is not None:
            parts.append(f"{src} -> {dst}")
        for field in ("dataset", "updated"):
            v = r.get(field)
            if v is not None:
                parts.append(f"{field}={v}")
        if not parts:
            return f"Task({self.key})"
        return f"Task({self.key}, {', '.join(parts)})"

    def set_status(self, status):
        self.patch([{"op": "add", "path": "/status", "value": status}], robust=True)

    def unregister(self):
        # deleting a task is unprotected because non-admin should be able to delete their tasks
        return self.unprotected_unregister()

    def take_ownership(self, steal_if_stale_after_seconds=None):
        """Take ownership of a queued task.

        Parameters
        ----------
        steal_if_stale_after_seconds : int, optional
            If provided and the task is already in the ``running`` state,
            inspect its worker timestamp. When the last update is older than
            this many seconds, release the previous ownership and retake the
            task. Otherwise, ``TaskNotQueuedError`` is raised.
            If ``None`` (default), no stale-takeover is attempted and
            ``TaskNotQueuedError`` is raised whenever the task is not in the
            ``queued`` state.

        Raises
        ------
        TaskNotQueuedError
            If the task is not in the ``queued`` state and cannot (or should
            not) be stolen from a stale worker.
        """
        from requests import HTTPError

        trace = trace_info()
        trace["timestamp"] = datetime.datetime.now().isoformat()

        def _claim():
            return self.patch(
                [
                    {"op": "test", "path": "/status", "value": "queued"},
                    {"op": "replace", "path": "/status", "value": "running"},
                    {"op": "add", "path": "/worker", "value": trace},
                ]
            )

        try:
            return _claim()
        except HTTPError as exc:
            if exc.response is None or exc.response.status_code != 400:
                raise

            if steal_if_stale_after_seconds is None:
                raise TaskNotQueuedError(f"Task {self.key!r} is not in 'queued' state") from exc

            worker = self.record.get("worker", {})
            ts_str = worker.get("timestamp")
            if not ts_str:
                raise TaskNotQueuedError(
                    f"Task {self.key!r} is not in 'queued' state and has no worker timestamp"
                ) from exc

            age = (datetime.datetime.now() - datetime.datetime.fromisoformat(ts_str)).total_seconds()
            if age < steal_if_stale_after_seconds:
                raise TaskNotQueuedError(
                    f"Task {self.key!r} is already running "
                    f"(last update {age:.0f}s ago, stale threshold {steal_if_stale_after_seconds}s)"
                ) from exc

            LOG.warning(
                "Task %s: stale ownership detected (last update %ds ago) — releasing and retaking",
                self.key, age,
            )
            self.release_ownership()
            return _claim()

    def release_ownership(self):
        self.patch(
            [
                {"op": "test", "path": "/status", "value": "running"},
                {"op": "replace", "path": "/status", "value": "queued"},
                {"op": "remove", "path": "/worker"},
            ]
        )

    def set_progress(self, progress):
        # progress can be a dict or an int
        if isinstance(progress, int):
            if not (0 <= progress <= 100):
                raise ValueError("Progress must be between 0 and 100")
            progress = dict(percent=progress)
        self.patch(
            [
                {"op": "test", "path": "/status", "value": "running"},
                {"op": "add", "path": "/progress", "value": progress},
            ],
            robust=True,
        )
