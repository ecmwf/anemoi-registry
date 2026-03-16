# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from anemoi.registry.rest import RestItemList

LOG = logging.getLogger(__name__)

COLLECTION = "resources"


class ResourceCatalogueEntryList(RestItemList):
    """List of resource catalogue entries."""

    def __init__(self):
        super().__init__(COLLECTION)

    def __iter__(self):
        for v in self.get():
            yield v

    def post(self, data: dict) -> dict:
        """Post a new resource to the catalogue.

        Parameters
        ----------
        data : dict
            The resource data to post.

        Returns
        -------
        dict
            The created resource as returned by the API.
        """
        return super().post(data)

    def get(self, params: dict | None = None) -> list:
        """Retrieve resources from the catalogue.

        Parameters
        ----------
        params : dict, optional
            Query parameters used to filter the results.

        Returns
        -------
        list
            List of matching resource dicts.
        """
        return self.rest.get(self.path, params=params)
