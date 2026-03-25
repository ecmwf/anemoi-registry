# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Unit tests for S3 upload/download logic — mocked, no real S3 access.

Tests cover path construction, catalogue patches during upload/download,
task lifecycle during transfer, and location management.
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Dataset — build_location_path
# ---------------------------------------------------------------------------


class TestBuildLocationPath:
    """Test URI pattern expansion for dataset locations."""

    def _make_entry(self, name="my-dataset"):
        """Build a minimal DatasetCatalogueEntry without hitting the server."""
        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.__new__(DatasetCatalogueEntry)
        entry.key = name
        entry.record = {"name": name, "metadata": {}, "locations": {}}
        entry._rest_item = MagicMock()
        return entry

    @patch("anemoi.registry.v1.entry.dataset.config")
    def test_default_pattern(self, mock_config):
        mock_config.return_value = {
            "datasets_platform": "ewc",
            "datasets_uri_pattern": "s3://ml-datasets-test/{name}.zarr",
        }
        entry = self._make_entry("aifs-ea-an-oper-v1")
        path = entry.build_location_path("ewc")
        assert path == "s3://ml-datasets-test/aifs-ea-an-oper-v1.zarr"

    def test_custom_pattern(self):
        entry = self._make_entry("my-ds")
        path = entry.build_location_path("atos", uri_pattern="/data/datasets/{name}")
        assert path == "/data/datasets/my-ds"


# ---------------------------------------------------------------------------
# Dataset — add_location / remove_location
# ---------------------------------------------------------------------------


class TestDatasetLocationPatches:
    def _make_entry(self, name="ds1"):
        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.__new__(DatasetCatalogueEntry)
        entry.key = name
        entry.record = {"name": name, "metadata": {}, "locations": {}}
        entry._rest_item = MagicMock()
        entry.patch = MagicMock()
        return entry

    def test_add_location_s3(self):
        entry = self._make_entry()
        result = entry.add_location("ewc", "s3://bucket/ds1.zarr")
        assert result == "s3://bucket/ds1.zarr"
        entry.patch.assert_called_once()
        patch_data = entry.patch.call_args[0][0]
        assert patch_data[0]["op"] == "add"
        assert patch_data[0]["path"] == "/locations/ewc"
        assert patch_data[0]["value"] == {"path": "s3://bucket/ds1.zarr"}

    def test_add_location_local_normalised(self):
        entry = self._make_entry()
        result = entry.add_location("local", "./relative/../data")
        # Local paths get normalised to absolute
        assert result.startswith("/")
        assert ".." not in result

    def test_remove_location(self):
        entry = self._make_entry()
        entry.remove_location("ewc")
        entry.patch.assert_called_once()
        patch_data = entry.patch.call_args[0][0]
        assert patch_data[0]["op"] == "remove"
        assert patch_data[0]["path"] == "/locations/ewc"


# ---------------------------------------------------------------------------
# Dataset — delete_location
# ---------------------------------------------------------------------------


class TestDatasetDeleteLocation:
    def _make_entry(self, platform="ewc", path="s3://bucket/ds1.zarr"):
        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.__new__(DatasetCatalogueEntry)
        entry.key = "ds1"
        entry.record = {"name": "ds1", "metadata": {}, "locations": {platform: {"path": path}}}
        entry._rest_item = MagicMock()
        entry.patch = MagicMock()
        return entry



# ---------------------------------------------------------------------------
# Dataset — transfer (task lifecycle during upload)
# ---------------------------------------------------------------------------


class TestDatasetTransfer:
    def _make_entry(self):
        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.__new__(DatasetCatalogueEntry)
        entry.key = "ds1"
        entry.record = {"name": "ds1", "metadata": {}}
        entry._rest_item = MagicMock()
        return entry

    @patch("anemoi.utils.remote.transfer")
    def test_transfer_success_unregisters_task(self, mock_transfer):
        entry = self._make_entry()
        task = MagicMock()
        entry.transfer(task, "/data/ds1.zarr", "s3://bucket/ds1.zarr", resume=True, threads=2)

        task.set_status.assert_called_once_with("running")
        mock_transfer.assert_called_once()
        task.unregister.assert_called_once()

    @patch("anemoi.utils.remote.transfer", side_effect=RuntimeError("S3 down"))
    def test_transfer_failure_stops_task(self, mock_transfer):
        entry = self._make_entry()
        task = MagicMock()
        with pytest.raises(RuntimeError, match="S3 down"):
            entry.transfer(task, "/data/ds1.zarr", "s3://bucket/ds1.zarr", resume=True, threads=2)

        # First call is "running", second call (on failure) is "stopped"
        assert task.set_status.call_args_list[0][0] == ("running",)
        assert task.set_status.call_args_list[1][0] == ("stopped",)
        task.unregister.assert_not_called()


# ---------------------------------------------------------------------------
# Weights — default_location / default_platform
# ---------------------------------------------------------------------------


class TestWeightsLocationPaths:
    def _make_entry(self, uuid="abc-123"):
        from anemoi.registry.v1.entry.weights import WeightCatalogueEntry

        entry = WeightCatalogueEntry.__new__(WeightCatalogueEntry)
        entry.key = uuid
        entry.record = {"uuid": uuid, "metadata": {}, "locations": {}}
        entry._rest_item = MagicMock()
        entry.patch = MagicMock()
        return entry

    @patch("anemoi.registry.v1.entry.weights.config")
    def test_default_location(self, mock_config):
        mock_config.return_value = {
            "weights_uri_pattern": "s3://ml-weights-test/{uuid}.ckpt",
        }
        entry = self._make_entry("abc-123")
        assert entry.default_location() == "s3://ml-weights-test/abc-123.ckpt"

    @patch("anemoi.registry.v1.entry.weights.config")
    def test_default_platform(self, mock_config):
        mock_config.return_value = {"weights_platform": "ewc"}
        entry = self._make_entry()
        assert entry.default_platform() == "ewc"


# ---------------------------------------------------------------------------
# Weights — upload / download (mocked S3)
# ---------------------------------------------------------------------------


class TestWeightsUploadDownload:
    def _make_entry(self, uuid="abc-123", locations=None):
        from anemoi.registry.v1.entry.weights import WeightCatalogueEntry

        entry = WeightCatalogueEntry.__new__(WeightCatalogueEntry)
        entry.key = uuid
        entry.record = {"uuid": uuid, "metadata": {}, "locations": locations or {}}
        entry._rest_item = MagicMock()
        entry.patch = MagicMock()
        return entry

    @patch("anemoi.registry.v1.entry.weights.upload")
    @patch("anemoi.registry.v1.entry.weights.config")
    def test_upload_default_target(self, mock_config, mock_upload):
        mock_config.return_value = {"weights_uri_pattern": "s3://ml-weights/{uuid}.ckpt"}
        entry = self._make_entry("abc-123")
        target = entry.upload("/tmp/model.ckpt")
        assert target == "s3://ml-weights/abc-123.ckpt"
        mock_upload.assert_called_once_with(
            "/tmp/model.ckpt", "s3://ml-weights/abc-123.ckpt",
            overwrite=False, resume=True,
        )

    @patch("anemoi.registry.v1.entry.weights.upload")
    def test_upload_custom_target(self, mock_upload):
        entry = self._make_entry()
        target = entry.upload("/tmp/model.ckpt", target="s3://custom/path.ckpt")
        assert target == "s3://custom/path.ckpt"
        mock_upload.assert_called_once()

    @patch("anemoi.registry.v1.entry.weights.download")
    def test_download_calls_s3(self, mock_download):
        entry = self._make_entry(
            locations={"ewc": {"path": "s3://ml-weights/abc-123.ckpt"}}
        )
        entry.download("/tmp/out.ckpt", "ewc")
        mock_download.assert_called_once_with(
            "s3://ml-weights/abc-123.ckpt", "/tmp/out.ckpt", resume=True,
        )

    @patch("anemoi.registry.v1.entry.weights.download")
    def test_download_missing_platform_no_crash(self, mock_download):
        entry = self._make_entry(locations={"ewc": {"path": "s3://x"}})
        # Should log error but not crash
        entry.download("/tmp/out.ckpt", "nonexistent")
        mock_download.assert_not_called()


# ---------------------------------------------------------------------------
# Dataset — set_recipe
# ---------------------------------------------------------------------------


class TestDatasetSetRecipe:
    def _make_entry(self):
        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.__new__(DatasetCatalogueEntry)
        entry.key = "ds1"
        entry.record = {"name": "ds1", "metadata": {}}
        entry._rest_item = MagicMock()
        entry.patch = MagicMock()
        return entry

    def test_set_recipe_from_dict(self):
        entry = self._make_entry()
        entry.set_recipe({"input": {"mars": {"param": "2t"}}})
        entry.patch.assert_called_once()
        patch_data = entry.patch.call_args[0][0]
        assert patch_data[0]["op"] == "add"
        assert patch_data[0]["path"] == "/metadata/recipe"

    def test_set_recipe_from_file(self, tmp_path):
        recipe_file = tmp_path / "recipe.yaml"
        recipe_file.write_text("input:\n  mars:\n    param: 2t\n")
        entry = self._make_entry()
        entry.set_recipe(str(recipe_file))
        entry.patch.assert_called_once()
        patch_data = entry.patch.call_args[0][0]
        assert patch_data[0]["value"]["input"]["mars"]["param"] == "2t"
