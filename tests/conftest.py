# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Shared pytest fixtures for anemoi-registry tests.

Layers
------
- **unit** : HTTP mocked, no server needed.  Runs everywhere.
- **integration** : Hits the live test catalogue (``ANEMOI_CATALOGUE=TEST``).
- **cli** : Subprocess invocations of ``anemoi-registry`` against the test catalogue.
"""

import importlib
import os
import shlex
import subprocess
import uuid

import pytest

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: requires live test server (ANEMOI_CATALOGUE=TEST)")
    config.addinivalue_line("markers", "cli: tests running the CLI via subprocess")
    config.addinivalue_line("markers", "s3: requires S3 credentials and test buckets")


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _force_test_env(monkeypatch):
    """Ensure every test talks to the test catalogue, never production."""
    monkeypatch.setenv("ANEMOI_CATALOGUE", "TEST")


@pytest.fixture(params=["1", "2"], ids=["v1", "v2"])
def cli_version(request, monkeypatch):
    """Parametrise a test to run under both v1 and v2.

    Sets ``ANEMOI_REGISTRY_CLI_VERSION`` and forces a re-import of the
    ``anemoi.registry`` package so the correct version module is active.
    """
    monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", request.param)
    # Invalidate cached module state
    import anemoi.registry

    importlib.reload(anemoi.registry)
    return request.param


@pytest.fixture
def v1_only(monkeypatch):
    monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", "1")
    import anemoi.registry

    importlib.reload(anemoi.registry)


@pytest.fixture
def v2_only(monkeypatch):
    monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", "2")
    import anemoi.registry

    importlib.reload(anemoi.registry)


# ---------------------------------------------------------------------------
# Unique identifiers (per-test isolation)
# ---------------------------------------------------------------------------


@pytest.fixture
def unique_id():
    """Short unique hex string for test-data isolation."""
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------


@pytest.fixture
def run_cli():
    """Return a helper that calls ``anemoi-registry`` as a subprocess.

    The returned callable accepts positional string arguments and returns
    a ``subprocess.CompletedProcess``.  ``ANEMOI_CATALOGUE`` is always
    set to ``TEST``.
    """

    def _run(*args, version=None, check=True):
        env = os.environ.copy()
        env["ANEMOI_CATALOGUE"] = "TEST"
        if version is not None:
            env["ANEMOI_REGISTRY_CLI_VERSION"] = str(version)
        cmd = ["anemoi-registry", *args]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        if check:
            if result.returncode != 0:
                msg = (
                    f"CLI failed: {shlex.join(cmd)} (rc={result.returncode})\n"
                    f"--- stdout ---\n{result.stdout}\n"
                    f"--- stderr ---\n{result.stderr}"
                )
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
        return result

    return _run


# ---------------------------------------------------------------------------
# REST client (for integration tests that talk to the server directly)
# ---------------------------------------------------------------------------


@pytest.fixture
def rest_client():
    """A pre-configured ``Rest`` client pointing at the test catalogue."""
    from anemoi.registry.v1.rest import Rest

    return Rest()


@pytest.fixture
def experiment_yaml(tmp_path):
    """Create a minimal experiment YAML in a temporary directory."""
    path = tmp_path / "test-experiment.yaml"
    expver = f"t{uuid.uuid4().hex[:3]}"
    path.write_text(f"description: Test experiment\n" f"metadata:\n" f"  expver: {expver}\n" f"  owner: ci-test\n")
    return str(path), expver
