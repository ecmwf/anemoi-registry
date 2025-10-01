# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging
import os

from anemoi.utils.checkpoints import load_metadata as load_checkpoint_metadata
from anemoi.utils.remote.s3 import download
from anemoi.utils.remote.s3 import upload

from anemoi.registry.rest import RestItemList

from .. import config
from . import CatalogueEntry

COLLECTION = "weights"

LOG = logging.getLogger(__name__)


class WeightsCatalogueEntryList(RestItemList):
    """List of weights catalogue entries."""

    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield WeightCatalogueEntry.load_from_key(key=v["uuid"])


class WeightCatalogueEntry(CatalogueEntry):
    collection = COLLECTION
    main_key = "uuid"

    def add_location(self, platform, path):
        self.patch([{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}], robust=True)
        return path

    def default_location(self, **kwargs):
        uri = config()["weights_uri_pattern"]
        uri = uri.format(uuid=self.key, **kwargs)
        return uri

    def default_platform(self):
        return config()["weights_platform"]

    def download(self, path, platform):
        """Download the weights to the specified path."""
        LOG.info(f"Downloading {self.key} to {path}.")
        dirname = os.path.dirname(path)
        if dirname and not os.path.exists(dirname):
            LOG.info(f"Creating directory {dirname} for downloading weights.")
            os.makedirs(dirname, exist_ok=True)
        if self.record.get("locations") is None:
            LOG.error(f"No locations found for {self.key}. Cannot download.")
            return
        if platform not in self.record["locations"]:
            LOG.error(
                f"Platform {platform} not found in locations for {self.key}. Available platforms: {list(self.record['locations'].keys())}"
            )
            return
        source = self.record["locations"][platform]["path"]
        download(source, path, resume=True)

    def upload(self, path, target=None, overwrite=False):
        if target is None:
            target = self.default_location()

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=overwrite, resume=not overwrite)
        return target

    def register(self, upload=False, **kwargs):
        assert self.path is not None, "path must be provided"

        super().register(**kwargs)

        if upload:
            platform = self.default_platform()
            target = self.upload(self.path)
            self.add_location(platform=platform, path=target)

    @classmethod
    def load_from_path(cls, path):
        assert os.path.exists(path), f"{path} does not exist"

        metadata = load_checkpoint_metadata(path)
        assert "path" not in metadata
        metadata["path"] = os.path.abspath(path)

        metadata["size"] = os.path.getsize(path)

        uuid = metadata.get("uuid")
        if uuid is None:
            uuid = metadata["run_id"]
            LOG.warning(f"Could not find 'uuid' in {path}, using 'run_id' instead: {uuid}")

        return cls(
            uuid,
            dict(uuid=uuid, metadata=metadata),
            path=path,
        )

    @classmethod
    def search_requests(cls, **kwargs):
        """Get the request for the entry."""
        requests = super().search_requests(**kwargs)
        request = dict(name=kwargs["NAME_OR_PATH"], type=kwargs["type"])
        requests.append(request)
        return requests
