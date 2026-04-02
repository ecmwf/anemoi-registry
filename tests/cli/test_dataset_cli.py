# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""CLI tests for dataset operations — register from zarr, metadata, locations.

These require real S3 access (to download the reference zarr) so they are
marked ``s3``.  Run with::

    pytest -m s3 tests/cli/test_dataset_cli.py
"""

import os
import shutil
import uuid

import pytest
import yaml
import zarr

IN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cli,
    pytest.mark.s3,
    pytest.mark.skipif(IN_GITHUB, reason="No catalogue token available in GitHub Actions"),
]

REFERENCE_ARCHIVE = "anemoi-datasets/create/mock-mars-0.14/pipe.zarr.tgz"
BASE_DATASET_NAME = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"


@pytest.fixture(scope="module")
def cached_zarr(tmp_path_factory):
    """Download the reference zarr once for the module (cached by path)."""
    import urllib.request

    from anemoi.utils.testing import TEST_DATA_URL

    cache = tmp_path_factory.mktemp("zarr_cache")
    url = f"{TEST_DATA_URL}{REFERENCE_ARCHIVE}"
    archive = str(cache / "pipe.zarr.tgz")
    urllib.request.urlretrieve(url, archive)  # noqa: S310
    shutil.unpack_archive(archive, str(cache))

    local = str(cache / "pipe.zarr")
    assert os.path.exists(local)
    return local


@pytest.fixture()
def dataset_env(cached_zarr, tmp_path):
    """Create a unique copy of the zarr with a fresh UUID and matching recipe.

    Yields ``(zarr_path, dataset_name, recipe_path)`` and cleans up via
    the CLI afterwards.
    """
    pid = os.getpid()
    suffix = uuid.uuid4().hex[:6]
    name = f"{BASE_DATASET_NAME}-{pid}-{suffix}"
    zarr_path = str(tmp_path / f"{name}.zarr")

    shutil.copytree(cached_zarr, zarr_path)
    z = zarr.open(zarr_path)
    z.attrs["uuid"] = str(uuid.uuid4())

    # Build a recipe file with the right name
    recipe_src = os.path.join(os.path.dirname(__file__), "..", "recipe.yaml")
    with open(recipe_src) as f:
        recipe = yaml.safe_load(f)
    recipe["name"] = name
    recipe_path = str(tmp_path / f"{name}.yaml")
    with open(recipe_path, "w") as f:
        yaml.dump(recipe, f)

    yield zarr_path, name, recipe_path


# -------------------------------------------------------------------
# v1 dataset lifecycle
# -------------------------------------------------------------------


class TestDatasetRegisterV1:
    """Register a dataset from a local zarr, manipulate metadata, unregister."""

    def test_register_and_unregister(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            # Register
            run_cli("datasets", zarr_path, "--register", version="1")

            # Read back
            run_cli("datasets", name, version="1")
        finally:
            run_cli("datasets", name, "--unregister", version="1", check=False)

    def test_set_recipe(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("datasets", zarr_path, "--register", version="1")
            run_cli("datasets", name, "--set-recipe", recipe_path, version="1")
        finally:
            run_cli("datasets", name, "--unregister", version="1", check=False)

    def test_set_status(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("datasets", zarr_path, "--register", version="1")
            run_cli("datasets", name, "--set-status", "testing", version="1")
        finally:
            run_cli("datasets", name, "--unregister", version="1", check=False)

    def test_add_location(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("datasets", zarr_path, "--register", version="1")

            # Named platform with uri-pattern
            run_cli(
                "datasets",
                name,
                "--add-location",
                "atos",
                "--uri-pattern",
                "/the/dataset/path/{name}",
                version="1",
            )

            # Another platform
            run_cli(
                "datasets",
                name,
                "--add-location",
                "leonardo",
                "--uri-pattern",
                "https://other/{name}/path",
                version="1",
            )

            # Platform with default uri
            run_cli("datasets", name, "--add-location", "ewc", version="1")
        finally:
            run_cli("datasets", name, "--unregister", version="1", check=False)

    def test_set_and_remove_metadata(self, run_cli, dataset_env):
        """Set metadata of various types, verify via Python API, then remove."""
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("datasets", zarr_path, "--register", version="1")

            run_cli("datasets", name, "--set-metadata", "TEST={}", "yaml", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.a={}", "yaml", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.a.string=ok", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.a.int=42", "int", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.a.float=42", "float", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.a.datetime=2015-04-18", "datetime", version="1")
            run_cli("datasets", name, "--set-metadata", "TEST.c={a: 43}", "yaml", version="1")

            test_json = os.path.join(os.path.dirname(__file__), "..", "test.json")
            run_cli("datasets", name, "--set-metadata", f"TEST.d={test_json}", "path", version="1")

            # Verify via Python API
            from anemoi.registry import Dataset

            actual = Dataset(name).record["metadata"]["TEST"]
            expected = {
                "a": {"string": "ok", "int": 42, "float": 42.0, "datetime": "2015-04-18T00:00:00"},
                "c": {"a": 43},
                "d": {"a": 45},
            }
            assert actual == expected, f"metadata mismatch: {actual!r} != {expected!r}"

            # Remove and verify
            run_cli("datasets", name, "--remove-metadata", "TEST", version="1")
            metadata = Dataset(name).record["metadata"]
            assert "TEST" not in metadata, f"TEST still in metadata: {metadata.get('TEST')}"
        finally:
            run_cli("datasets", name, "--unregister", version="1", check=False)


# -------------------------------------------------------------------
# v2 dataset lifecycle (no location management in v2)
# -------------------------------------------------------------------


class TestDatasetRegisterV2:
    """Register a dataset from a local zarr via v2, manipulate metadata, unregister."""

    def test_register_and_unregister(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("dataset", "--register", zarr_path, version="2")
            run_cli("dataset", name, version="2")
        finally:
            run_cli("dataset", name, "--unregister", version="2", check=False)

    def test_set_recipe(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("dataset", "--register", zarr_path, version="2")
            run_cli("dataset", name, "--set-recipe", recipe_path, version="2")
        finally:
            run_cli("dataset", name, "--unregister", version="2", check=False)

    def test_set_status(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("dataset", "--register", zarr_path, version="2")
            run_cli("dataset", name, "--set-status", "testing", version="2")
        finally:
            run_cli("dataset", name, "--unregister", version="2", check=False)

    def test_set_and_remove_metadata(self, run_cli, dataset_env):
        zarr_path, name, recipe_path = dataset_env
        try:
            run_cli("dataset", "--register", zarr_path, version="2")

            run_cli("dataset", name, "--metadata", "set", "TEST={}", "yaml", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.a={}", "yaml", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.a.string=ok", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.a.int=42", "int", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.a.float=42", "float", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.a.datetime=2015-04-18", "datetime", version="2")
            run_cli("dataset", name, "--metadata", "set", "TEST.c={a: 43}", "yaml", version="2")

            test_json = os.path.join(os.path.dirname(__file__), "..", "test.json")
            run_cli("dataset", name, "--metadata", "set", f"TEST.d={test_json}", "path", version="2")

            from anemoi.registry import Dataset

            actual = Dataset(name).record["metadata"]["TEST"]
            expected = {
                "a": {"string": "ok", "int": 42, "float": 42.0, "datetime": "2015-04-18T00:00:00"},
                "c": {"a": 43},
                "d": {"a": 45},
            }
            assert actual == expected, f"metadata mismatch: {actual!r} != {expected!r}"

            run_cli("dataset", name, "--metadata", "delete", "TEST", version="2")
            metadata = Dataset(name).record["metadata"]
            assert "TEST" not in metadata, f"TEST still in metadata: {metadata.get('TEST')}"
        finally:
            run_cli("dataset", name, "--unregister", version="2", check=False)
