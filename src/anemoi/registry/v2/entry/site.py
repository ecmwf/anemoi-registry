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
    """A single site entry in the catalogue.

    Sites are identified by name.  Their server-side representation
    is derived from ``db.resources`` (quota data posted by site agents)
    and ``sites/<name>.json`` config files on the server.

    For local steward operations (monitoring, transfers, etc.) use
    :class:`~anemoi.registry.v2.site.Site` instead.
    """

    collection = COLLECTION

    def __init__(self, name, record=None):
        self.name = name
        self.record = record

    @property
    def key(self):
        return self.name

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
        base_url = f"{rest.api_url}/sites/{self.name}"
        url = f"{base_url}/resources"
        response = rest.session.get(url)
        rest.raise_for_status(response)
        return response.json()

    def __repr__(self):
        return f"SiteCatalogueEntry({self.name!r})"
