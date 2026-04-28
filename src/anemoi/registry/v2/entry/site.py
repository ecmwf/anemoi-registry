# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site catalogue entry — a named site with config, storage quotas, and replicas."""

import logging

from ..rest import Rest
from ..rest import RestItemList

LOG = logging.getLogger(__name__)

COLLECTION = "sites"


class SiteCatalogueEntryList:
    """List known sites via the ``api/v1/sites`` endpoint."""

    def __init__(self, **params):
        self._params = params

    def get(self, params=None):
        """List sites."""
        merged = dict(self._params)
        if params:
            merged.update(params)
        return RestItemList(COLLECTION).get(params=merged)

    def __iter__(self):
        for v in self.get():
            name = v.get("name") or v.get("site")
            yield SiteCatalogueEntry(name=name, record=v)

    def __len__(self):
        return len(self.get())


class SiteCatalogueEntry:
    """A single site entry.

    Sites are identified by name.  Their server-side representation
    is derived from ``db.resources`` (quota data posted by site agents)
    and ``sites/<name>.json`` config files on the server.

    This entry class provides convenience accessors for:
    - bootstrap setup (``setup``)
    - config fetching (``load_config``)
    - quota/storage monitoring (``report_storage``)
    - replica status (``report_datasets``)
    - auxiliary file downloads (``update_auxiliary``)
    """

    collection = COLLECTION

    def __init__(self, name, record=None, base_url=None):
        self.name = name
        self.record = record
        self._base_url_override = base_url

    @property
    def key(self):
        return self.name

    # ------------------------------------------------------------------
    # Bootstrap / setup
    # ------------------------------------------------------------------

    def setup(self, url) -> None:
        """Run first-time bootstrap for this site.

        Parameters
        ----------
        url : str
            Full API URL, e.g.
            ``https://server/api/v1/sites/<site>``.
        """
        from ..site import Site

        Site.setup(url)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def load_config(self, section=None) -> dict:
        """Load site config (or a specific section).

        Parameters
        ----------
        section : str, optional
            If given, load only this section (e.g. ``"monitoring"``).
            Otherwise load the full bootstrap.
        """
        from ..site import Site

        site = Site.current()
        if section is None:
            return site.data
        return site.task_config(section)

    @property
    def base_url(self):
        """Return the configured base URL from bootstrap."""
        if self._base_url_override:
            return self._base_url_override
        from ..site import Site

        return Site.current().base_url

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def report_storage(self, dry_run=False):
        """Run quota commands and POST results to the server."""
        from ..site import Site

        Site.current().report_storage(dry_run=dry_run)

    def report_datasets(self, dry_run=False):
        """Check replica status locally and POST updates."""
        from ..site import Site

        Site.current().report_datasets(dry_run=dry_run)

    # ------------------------------------------------------------------
    # Auxiliary files
    # ------------------------------------------------------------------

    def update_auxiliary(self, dry_run=False):
        """Download auxiliary files from remote storage."""
        from ..site import Site

        Site.current().update_auxiliary(dry_run=dry_run)

    # ------------------------------------------------------------------
    # Replicas for this site
    # ------------------------------------------------------------------

    def replicas(self):
        """Return replicas registered on this site."""
        from .replica import ReplicaCatalogueEntryList

        return ReplicaCatalogueEntryList(site=self.name)

    # ------------------------------------------------------------------
    # Resources (quota) for this site
    # ------------------------------------------------------------------

    def resources(self):
        """Fetch resource/quota records for this site from the API."""
        rest = Rest()
        url = f"{self.base_url}/resources"
        response = rest.session.get(url)
        rest.raise_for_status(response)
        return response.json()

    def __repr__(self):
        return f"SiteCatalogueEntry({self.name!r})"
