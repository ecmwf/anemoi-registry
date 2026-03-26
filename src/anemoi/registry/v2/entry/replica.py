# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Replica catalogue entry — a dataset location on a specific site."""

import logging
import os

from .. import config
from ..rest import Rest
from ..rest import RestItemList
from ..tasks import TaskCatalogueEntryList

LOG = logging.getLogger(__name__)

COLLECTION = "replicas"


class ReplicaCatalogueEntryList:
    """Query the replicas collection (read) and the site replicas endpoint (write)."""

    def __init__(self, **params):
        self._params = params

    def get(self, params=None):
        """List replicas from api/v1/replicas with optional filters."""
        merged = dict(self._params)
        if params:
            merged.update(params)
        return RestItemList(COLLECTION).get(params=merged)

    def __iter__(self):
        for v in self.get():
            yield ReplicaCatalogueEntry.from_record(v)

    def __len__(self):
        return len(self.get())

    def __bool__(self):
        return len(self) > 0


class ReplicaCatalogueEntry:
    """A single replica — one (dataset, site) pair.

    Replicas are a denormalised view of ``datasets.locations.<site>``.
    Reads come from ``api/v1/replicas``; mutations go through the
    dataset entry's ``locations`` sub-document.
    """

    collection = COLLECTION

    def __init__(self, dataset_name, site, record=None):
        self.dataset_name = dataset_name
        self.site = site
        self.record = record

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_record(cls, record):
        """Build from a replica document returned by the API."""
        name = record.get("name") or record.get("dataset")
        site = record.get("site")
        return cls(dataset_name=name, site=site, record=record)

    @classmethod
    def from_dataset_entry(cls, dataset_entry, site):
        """Build from an existing DatasetCatalogueEntry and a site name."""
        locations = dataset_entry.record.get("locations", {})
        loc = locations.get(site, {})
        record = {
            "name": dataset_entry.key,
            "site": site,
            "path": loc.get("path", ""),
        }
        return cls(dataset_name=dataset_entry.key, site=site, record=record)

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    @property
    def path(self):
        if self.record:
            return self.record.get("path", "")
        return ""

    @property
    def key(self):
        return f"{self.dataset_name}@{self.site}"

    # ------------------------------------------------------------------
    # Mutations (delegate to DatasetCatalogueEntry)
    # ------------------------------------------------------------------

    def _dataset_entry(self):
        from .dataset import DatasetCatalogueEntry

        return DatasetCatalogueEntry(key=self.dataset_name)

    def register(self, path=None, uri_pattern=None, upload=False, source_path=None) -> None:
        """Register this replica location on the dataset.

        Parameters
        ----------
        path : str, optional
            Explicit path for the location.  If *None*, built from
            ``uri_pattern`` or the default config.
        uri_pattern : str, optional
            URI pattern containing ``{name}``.
        upload : bool
            Whether to upload local data before registering.
        source_path : str, optional
            Local path to upload from (required when *upload* is True).
        """
        entry = self._dataset_entry()

        if path is None:
            if source_path and os.path.exists(source_path) and not upload and not uri_pattern:
                # Local path registration (like the old --add-local)
                entry.add_location(self.site, path=source_path)
                return
            path = entry.build_location_path(platform=self.site, uri_pattern=uri_pattern)

        if upload:
            if source_path is None or not os.path.exists(source_path):
                raise ValueError("source_path must be an existing local path when uploading.")
            entry.upload(source=source_path, target=path, platform=self.site)

        LOG.info(f"Adding location to {self.site}: {path}")
        entry.add_location(platform=self.site, path=path)

    def unregister(self):
        """Remove this location from the catalogue (data is kept)."""
        self._dataset_entry().remove_location(self.site)

    def delete(self):
        """Delete the replica data and remove the location."""
        self._dataset_entry().delete_location(self.site)

    def request_transfer(self, uri_pattern=None) -> str:
        """Create a task to transfer this dataset to the site.

        Parameters
        ----------
        uri_pattern : str, optional
            URI pattern containing ``{name}``.

        Returns
        -------
        str
            UUID of the created task.
        """
        entry = self._dataset_entry()
        path = entry.build_location_path(platform=self.site, uri_pattern=uri_pattern)
        uuid = TaskCatalogueEntryList().add_new_task(
            action="transfer-dataset",
            source="cli",
            destination=self.site,
            target_path=path,
            dataset=self.dataset_name,
        )
        return uuid

    def request_deletion(self) -> str:
        """Create a task to delete this replica.

        Returns
        -------
        str
            UUID of the created task.
        """
        uuid = TaskCatalogueEntryList().add_new_task(
            action="delete-dataset",
            source="cli",
            destination=self.site,
            dataset=self.dataset_name,
        )
        return uuid

    def update_status(self, real_path=None, last_accessed=None):
        """POST status update to the site replicas endpoint."""
        base_url = config().get("api_url", "")
        entry_point = f"{base_url}/sites/{self.site}/replicas"
        payload = {"dataset": self.dataset_name}
        if real_path is not None:
            payload["real_path"] = real_path
        if last_accessed is not None:
            payload["last_accessed"] = last_accessed

        rest = Rest()
        response = rest.session.post(entry_point, json=payload)
        rest.raise_for_status(response)
        return response.json()

    def __repr__(self):
        return f"ReplicaCatalogueEntry({self.dataset_name!r}, {self.site!r})"
