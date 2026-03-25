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

from ..rest import Rest, RestItemList

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

    def __init__(self, name, record=None):
        self.name = name
        self.record = record

    @property
    def key(self):
        return self.name

    # ------------------------------------------------------------------
    # Bootstrap / setup
    # ------------------------------------------------------------------

    def setup(self, url):
        """Run first-time bootstrap for this site.

        Parameters
        ----------
        url : str
            Full API URL, e.g.
            ``https://server/api/v1/sites/<site>``.
        """
        from ..site.bootstrap import setup_bootstrap

        setup_bootstrap(url)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def load_config(self, section=None):
        """Load site config (or a specific section).

        Parameters
        ----------
        section : str, optional
            If given, load only this section (e.g. ``"monitoring"``).
            Otherwise load the full bootstrap.
        """
        if section is None:
            from ..site.bootstrap import load_bootstrap

            return load_bootstrap()

        from ..site.config import load_site_config

        return load_site_config(section)

    @property
    def base_url(self):
        """Return the configured base URL from bootstrap."""
        from ..site.bootstrap import load_bootstrap

        bootstrap = load_bootstrap()
        url = bootstrap.get("base_url")
        if not url:
            raise ValueError(
                "No base_url in bootstrap config. "
                "Run: anemoi-registry site --setup URL"
            )
        return url

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def report_storage(self, dry_run=False):
        """Run quota commands and POST results to the server."""
        from ..site.monitoring import SiteStatus, load_monitoring_manifest

        manifest = load_monitoring_manifest()
        status = SiteStatus(manifest)
        status.report_storage(self.base_url, is_test=dry_run)

    def report_datasets(self, dry_run=False):
        """Check replica status locally and POST updates."""
        from ..site.monitoring import datasets_status

        datasets_status(self.base_url, is_test=dry_run)

    # ------------------------------------------------------------------
    # Auxiliary files
    # ------------------------------------------------------------------

    def update_auxiliary(self, dry_run=False):
        """Download auxiliary files from remote storage."""
        from ..site.auxiliary import update_auxiliary

        update_auxiliary(is_test=dry_run)

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
