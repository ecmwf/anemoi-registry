# (C) Copyright 2024-2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from types import SimpleNamespace

import numpy as np
import zarr

from anemoi.registry.entry.dataset import DatasetCatalogueEntry


def test_load_from_path_reads_data_shape(tmp_path, monkeypatch):
    """The shape comes from ``z["data"]``: attribute access to group members does not exist in zarr 3."""
    path = tmp_path / "test.zarr"
    group = zarr.open_group(str(path), mode="w")
    kwargs = dict(shape=(4, 2, 1, 3), chunks=(1, 2, 1, 3), dtype="f4")
    if hasattr(group, "create_array"):  # zarr 3
        group.create_array("data", **kwargs)
    else:  # zarr 2, which this package is still tested with (anemoi-datasets pins zarr<=2.18.7)
        group.create_dataset("data", **kwargs)
    group.attrs["start_date"] = "2020-01-01T00:00:00"

    stats = {k: np.zeros(2) for k in ("mean", "stdev", "minimum", "maximum")}
    dataset = SimpleNamespace(statistics=stats, dtype=np.dtype("f4"), chunks=(1, 2, 1, 3))
    monkeypatch.setattr("anemoi.datasets.open_dataset", lambda path: dataset)

    entry = DatasetCatalogueEntry.load_from_path(str(path))

    assert tuple(entry.record["metadata"]["shape"]) == (4, 2, 1, 3)
