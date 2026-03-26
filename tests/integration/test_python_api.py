# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Integration tests — Python API against the live test server.

These tests exercise the Python classes (``Dataset``, ``Experiment``, etc.)
against the running test catalogue at ``ANEMOI_CATALOGUE=TEST``.
They create ephemeral entries, verify them, and clean up.
No S3 uploads or downloads are performed.
"""

import importlib
import uuid

import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reload_registry(version):
    """Force-reload the registry package for the given version string."""
    import os

    os.environ["ANEMOI_REGISTRY_CLI_VERSION"] = version
    import anemoi.registry as reg

    importlib.reload(reg)
    return reg


# ---------------------------------------------------------------------------
# Configuration (read-only, safe)
# ---------------------------------------------------------------------------


class TestConfig:
    """Verify config() returns sane values from the test server."""

    def test_config_returns_api_url(self):
        from anemoi.registry import config

        c = config()
        assert "api_url" in c
        assert "test" in c["api_url"].lower()

    def test_config_returns_web_url(self):
        from anemoi.registry import config

        c = config()
        assert "web_url" in c

    def test_config_has_expected_keys(self):
        from anemoi.registry import config

        c = config()
        for key in ("api_url", "web_url", "datasets_platform", "datasets_uri_pattern"):
            assert key in c, f"Expected key '{key}' in config"


# ---------------------------------------------------------------------------
# Listing (read-only, safe)
# ---------------------------------------------------------------------------


class TestListEntries:
    """List operations via REST — read-only, no data created.

    Uses the REST client directly to avoid iterating all entries
    (which is slow and can fail on bad data in the test database).
    """

    @pytest.mark.parametrize("collection", ["datasets", "experiments", "weights", "tasks"])
    def test_list_returns_list(self, rest_client, collection):
        data = rest_client.get(collection)
        assert isinstance(data, list)
        assert len(data) > 0, f"Expected at least one entry in '{collection}'"


# ---------------------------------------------------------------------------
# Experiment CRUD (creates + cleans up)
# ---------------------------------------------------------------------------


class TestExperimentCRUD:
    """Register, read, patch, and unregister an experiment."""

    @pytest.mark.parametrize("version", ["1", "2"])
    def test_experiment_lifecycle(self, monkeypatch, version, experiment_yaml):
        reg = _reload_registry(version)
        yaml_path, expver = experiment_yaml

        from anemoi.registry.v1.entry.experiment import ExperimentCatalogueEntry

        entry = ExperimentCatalogueEntry.load_from_path(yaml_path)

        try:
            # Register
            entry.register(ignore_existing=False)

            # Read back
            fetched = ExperimentCatalogueEntry.load_from_key(expver)
            assert fetched is not None
            assert fetched.key == expver

        finally:
            # Cleanup — always try to unregister
            try:
                entry.unprotected_unregister()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Task lifecycle
# ---------------------------------------------------------------------------


class TestTaskLifecycle:
    """Test the task state machine against the live server."""

    @pytest.mark.parametrize("version", ["1", "2"])
    def test_create_take_progress_delete(self, version):
        reg = _reload_registry(version)
        task_list = reg.TasksList()
        task_uuid = None

        try:
            # Create a new task
            task_uuid = task_list.add_new_task(
                action="dummy",
                status="queued",
                destination="test",
                source="test",
            )
            assert task_uuid is not None

            # Take ownership
            task = reg.Task(task_uuid)
            task.take_ownership()

            # Verify it's running
            task_refreshed = reg.Task(task_uuid)
            assert task_refreshed.record["status"] == "running"

            # Set progress
            task.set_progress(50)

            # Release
            task.release_ownership()

            # Verify it's back to queued
            task_refreshed2 = reg.Task(task_uuid)
            assert task_refreshed2.record["status"] == "queued"

        finally:
            if task_uuid:
                try:
                    t = reg.Task(task_uuid)
                    t.unregister()
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify proper exceptions for bad requests."""

    def test_nonexistent_dataset_raises(self):
        from anemoi.registry import CatalogueEntryNotFound
        from anemoi.registry import Dataset

        with pytest.raises(CatalogueEntryNotFound):
            Dataset(f"this-dataset-does-not-exist-{uuid.uuid4().hex[:8]}")

    def test_nonexistent_experiment_raises(self):
        from anemoi.registry import CatalogueEntryNotFound
        from anemoi.registry import Experiment

        with pytest.raises(CatalogueEntryNotFound):
            Experiment(f"x{uuid.uuid4().hex[:4]}")
