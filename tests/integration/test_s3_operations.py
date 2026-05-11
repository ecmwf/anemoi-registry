# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Integration tests that exercise real S3 operations.

These tests require S3 credentials (AWS config) and a running test catalogue.
Run with::

    pytest -m s3

They are skipped by default when running ``pytest`` without the ``-m s3`` flag.
"""

import os
import uuid

import pytest

IN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.s3,
    pytest.mark.skipif(IN_GITHUB, reason="No catalogue token available in GitHub Actions"),
]

# Skip the entire module if S3 credentials are not configured
try:
    from anemoi.utils.remote.s3 import upload as _s3_upload  # noqa: F401

    _HAS_S3 = True
except Exception:
    _HAS_S3 = False

if not _HAS_S3:
    pytest.skip("S3 credentials not available", allow_module_level=True)


# ---------------------------------------------------------------------------
# Weights — upload a tiny file then download it
# ---------------------------------------------------------------------------


class TestWeightsS3RoundTrip:
    """Upload a dummy checkpoint to the test bucket, verify, then clean up."""

    def test_upload_and_download(self, tmp_path):
        from anemoi.utils.remote.s3 import delete
        from anemoi.utils.remote.s3 import download
        from anemoi.utils.remote.s3 import upload

        # Create a tiny dummy file
        src = tmp_path / "dummy.ckpt"
        src.write_bytes(b"test-weights-content-" + uuid.uuid4().hex.encode())

        # Use the test bucket with a unique key
        key = f"test-{uuid.uuid4().hex[:8]}.ckpt"
        target = f"s3://ml-weights-test/{key}"

        try:
            upload(str(src), target, overwrite=True)

            dst = tmp_path / "downloaded.ckpt"
            download(target, str(dst))

            assert dst.read_bytes() == src.read_bytes()
        finally:
            # Always clean up
            try:
                delete(target)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Dataset — add_location round-trip via catalogue
# ---------------------------------------------------------------------------


class TestDatasetLocationRoundTrip:
    """Register a location in the catalogue, read it back, then remove it.

    This does NOT upload data to S3 — it only verifies the catalogue metadata
    operations work end-to-end.
    """

    def test_add_and_remove_location(self, rest_client):
        # Pick an existing dataset from the test catalogue
        datasets = rest_client.get("datasets", params={"limit": "1"})
        if not datasets:
            pytest.skip("No datasets on test server to test against")
        ds_name = datasets[0]["name"]

        from anemoi.registry.v1.entry.dataset import DatasetCatalogueEntry

        entry = DatasetCatalogueEntry.load_from_key(ds_name)
        if entry is None:
            pytest.skip(f"Dataset {ds_name} not found")

        platform = f"test-{uuid.uuid4().hex[:6]}"
        fake_path = f"s3://ml-datasets-test/test-{uuid.uuid4().hex[:8]}.zarr"

        try:
            entry.add_location(platform, fake_path)

            # Re-fetch to verify
            refreshed = DatasetCatalogueEntry.load_from_key(ds_name)
            assert platform in refreshed.record.get(
                "locations", {}
            ), f"Platform '{platform}' not in locations after add"
            assert refreshed.record["locations"][platform]["path"] == fake_path
        finally:
            try:
                entry.remove_location(platform)
            except Exception:
                pass
