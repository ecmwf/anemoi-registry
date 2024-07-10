# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import os

import yaml
from anemoi.utils.s3 import upload

from .. import config
from . import CatalogueEntry
from .weights import WeightCatalogueEntry

LOG = logging.getLogger(__name__)


class ExperimentCatalogueEntry(CatalogueEntry):
    collection = "experiments"
    main_key = "expver"

    def load_from_path(self, path):
        assert os.path.exists(path), f"{path} does not exist"
        assert path.endswith(".yaml"), f"{path} must be a yaml file"

        with open(path, "r") as file:
            config = yaml.safe_load(file)

        metadata = config.pop("metadata")
        metadata["config"] = config
        expver = metadata["expver"]

        self.key = expver
        self.record = dict(expver=expver, metadata=metadata)

    def add_plots(self, *paths, **kwargs):
        for path in paths:
            self._add_one_plot(path, **kwargs)

    def _add_one_plot(self, path, **kwargs):
        return self._add_one_plot_or_artefact("plot", path, **kwargs)

    def add_weights(self, *paths, **kwargs):
        for path in paths:
            self._add_one_weights(path, **kwargs)

    def add_artefacts(self, *paths, **kwargs):
        for path in paths:
            self._add_one_artefact(path, **kwargs)

    def _add_one_artefact(self, path, **kwargs):
        return self._add_one_plot_or_artefact("artefact", path, **kwargs)

    def _add_one_plot_or_artefact(self, kind, path, **kwargs):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Could not find {kind} to upload at {path}")

        target = config()[f"{kind}s_uri_pattern"]
        basename = os.path.basename(path)
        target = target.format(expver=self.key, basename=basename, filename=basename)

        LOG.info(f"Uploading {path} to {target}.")
        upload(path, target, overwrite=True)

        dic = dict(url=target, name=basename, path=path)
        self.rest_item.patch([{"op": "add", "path": f"/{kind}s/-", "value": dic}])

    def _add_one_weights(self, path, **kwargs):
        weights = WeightCatalogueEntry(path=path)
        if not WeightCatalogueEntry.key_exists(weights.key):
            weights.register(ignore_existing=False, overwrite=False)
            weights.upload(path, overwrite=False)
        else:
            other = WeightCatalogueEntry(key=weights.key)
            if other.record["metadata"]["timestamp"] == weights.record["metadata"]["timestamp"]:
                LOG.info(
                    f"Not updating weights with key={weights.key}, because it already exists and has the same timestamp"
                )
            else:
                raise ValueError(f"Conflicting weights with key={weights.key}")

        dic = dict(uuid=weights.key, path=path)
        self.rest_item.patch([{"op": "add", "path": "/checkpoints/-", "value": dic}])
