# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""CLI tests — subprocess invocations of ``anemoi-registry`` against the test catalogue.

These tests cover both v1 and v2 CLI layouts.  They use the ``run_cli``
fixture defined in the top-level conftest.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.cli]


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettingsCLI:
    """``anemoi-registry settings`` should succeed and print config."""

    @pytest.mark.parametrize("version", ["1", "2"])
    def test_settings_exits_zero(self, run_cli, version):
        result = run_cli("settings", version=version)
        assert result.returncode == 0

    @pytest.mark.parametrize("version", ["1", "2"])
    def test_settings_shows_api_url(self, run_cli, version):
        result = run_cli("settings", version=version)
        assert "api_url" in result.stdout.lower() or "api_url" in result.stderr.lower()


# ---------------------------------------------------------------------------
# List commands
# ---------------------------------------------------------------------------

class TestListCLI:
    """``anemoi-registry list <collection>`` (v1) / ``anemoi-registry <collection> --list`` (v2)."""

    @pytest.mark.parametrize("collection", ["datasets", "experiments", "weights"])
    def test_v1_list(self, run_cli, collection):
        result = run_cli("list", collection, version="1")
        assert result.returncode == 0

    @pytest.mark.parametrize("collection", ["dataset", "experiment", "weights"])
    def test_v2_list(self, run_cli, collection):
        result = run_cli(collection, "--list", version="2")
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestHelpCLI:
    """Every subcommand should respond to ``--help``."""

    @pytest.mark.parametrize("subcmd", [
        "datasets", "experiments", "weights", "list", "settings", "tasks",
    ])
    def test_v1_help(self, run_cli, subcmd):
        result = run_cli(subcmd, "--help", version="1")
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    @pytest.mark.parametrize("subcmd", [
        "dataset", "experiment", "weights", "settings", "task",
    ])
    def test_v2_help(self, run_cli, subcmd):
        result = run_cli(subcmd, "--help", version="2")
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Version flag
# ---------------------------------------------------------------------------

class TestVersionCLI:
    @pytest.mark.parametrize("version", ["1", "2"])
    def test_version_flag(self, run_cli, version):
        result = run_cli("--version", version=version)
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Experiment register / unregister via CLI
# ---------------------------------------------------------------------------

class TestExperimentCLICRUD:
    """Register and unregister an experiment through the CLI."""

    def test_v1_experiment_lifecycle(self, run_cli, experiment_yaml):
        yaml_path, expver = experiment_yaml

        try:
            # Register
            run_cli("experiments", yaml_path, "--register", version="1")

            # Read (should succeed without error)
            run_cli("experiments", expver, version="1")

        finally:
            # Cleanup
            run_cli("experiments", yaml_path, "--unregister", version="1", check=False)

    def test_v2_experiment_lifecycle(self, run_cli, experiment_yaml):
        yaml_path, expver = experiment_yaml

        try:
            run_cli("experiment", yaml_path, "--register", version="2")
            run_cli("experiment", expver, version="2")
        finally:
            run_cli("experiment", yaml_path, "--unregister", version="2", check=False)
