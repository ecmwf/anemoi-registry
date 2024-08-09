# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os

from anemoi.utils.checkpoints import load_metadata as load_checkpoint_metadata
from anemoi.utils.s3 import upload

from anemoi.registry.rest import RestItemList

from .. import config
from . import CatalogueEntry

COLLECTION = "weights"

LOG = logging.getLogger(__name__)


class WeightsCatalogueEntryList(RestItemList):
    def __init__(self, **kwargs):
        super().__init__(COLLECTION, **kwargs)

    def __iter__(self):
        for v in self.get():
            yield WeightCatalogueEntry(key=v["uuid"])


class WeightCatalogueEntry(CatalogueEntry):
    collection = COLLECTION
    main_key = "uuid"

    def add_location(self, platform, path):
        self.rest_item.patch([{"op": "add", "path": f"/locations/{platform}", "value": {"path": path}}])
        return path

    def default_location(self, **kwargs):
        uri = config()["weights_uri_pattern"]
        uri = uri.format(uuid=self.key, **kwargs)
        return uri

    def default_platform(self):
        return config()["weights_platform"]

    def upload(self, path, target=None, overwrite=False):
        if target is None:
            target = self.default_location()

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=overwrite, resume=not overwrite)
        return target

    def register(self, **kwargs):
        assert self.path is not None, "path must be provided"

        super().register(**kwargs)

        platform = self.default_platform()
        target = self.upload(self.path)
        self.add_location(platform=platform, path=target)

    def load_from_path(self, path):
        self.path = path
        assert os.path.exists(path), f"{path} does not exist"

        metadata = load_checkpoint_metadata(path)
        assert "path" not in metadata
        metadata["path"] = os.path.abspath(path)

        metadata["size"] = os.path.getsize(path)

        uuid = metadata.get("uuid")
        if uuid is None:
            uuid = metadata["run_id"]
            LOG.warning(f"Could not find 'uuid' in {path}, using 'run_id' instead: {uuid}")

        self.key = uuid
        self.record = dict(uuid=uuid, metadata=metadata)
