# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging

from anemoi.utils.humanize import when
from anemoi.utils.text import table

from anemoi.registry.entry import CatalogueEntry
from anemoi.registry.rest import RestItemList
from anemoi.registry.rest import trace_info
from anemoi.registry.utils import list_to_dict

LOG = logging.getLogger(__name__)


class TaskCatalogueEntryList:
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

        self.rest_collection = RestItemList(self.collection)

    def get(self):
        data = self.rest_collection.get(params=self.kwargs)
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

        # actor_factory(**kwargs).check()

        res = self.rest_collection.post(kwargs)
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
        uuid = res["uuid"]
        return uuid

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

    def set_status(self, status):
        patch = [{"op": "add", "path": "/status", "value": status}]
        self.rest_item.patch(patch)

    def unregister(self):
        # deleting a task is unprotected because non-admin should be able to delete their tasks
        return self.rest_item.unprotected_delete()

    def take_ownership(self):
        trace = trace_info()
        trace["timestamp"] = datetime.datetime.now().isoformat()
        return self.rest_item.patch(
            [
                {"op": "test", "path": "/status", "value": "queued"},
                {"op": "replace", "path": "/status", "value": "running"},
                {"op": "add", "path": "/worker", "value": trace},
            ]
        )

    def release_ownership(self):
        self.rest_item.patch(
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
        patch = [{"op": "add", "path": "/progress", "value": progress}]
        self.rest_item.patch(patch)
