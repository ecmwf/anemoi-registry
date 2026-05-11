# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Unit tests for :mod:`anemoi.registry.v*.configuration` — env var priority and URL selection."""

import importlib

import pytest

# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


class TestConfigURL:
    """Test that ``SingletonConfig.url`` respects the env-var priority chain."""

    def _make_config(self, monkeypatch, env_val=None):
        """Return a fresh ``SingletonConfig`` with the given ``ANEMOI_CATALOGUE`` value."""
        if env_val is not None:
            monkeypatch.setenv("ANEMOI_CATALOGUE", env_val)
        else:
            monkeypatch.delenv("ANEMOI_CATALOGUE", raising=False)

        # Force a fresh instance — SingletonConfig is a module-level singleton
        import anemoi.registry.v1.configuration as mod

        importlib.reload(mod)
        return mod.SingletonConfig()

    def test_test_shortcut(self, monkeypatch):
        cfg = self._make_config(monkeypatch, "TEST")
        url = cfg.url
        assert "test" in url.lower(), f"Expected test URL, got {url}"

    def test_explicit_url_from_env(self, monkeypatch):
        cfg = self._make_config(monkeypatch, "https://my-custom-server.example.com")
        assert cfg.url == "https://my-custom-server.example.com"


# ---------------------------------------------------------------------------
# Version selector
# ---------------------------------------------------------------------------


class TestVersionSelector:
    """Test ``ANEMOI_REGISTRY_CLI_VERSION`` routing."""

    def test_invalid_version_raises(self, monkeypatch):
        monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", "99")
        with pytest.raises(ValueError, match="Invalid ANEMOI_REGISTRY_CLI_VERSION"):
            import anemoi.registry as mod

            importlib.reload(mod)

    def test_version_1_loads_v1(self, monkeypatch):
        monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", "1")
        import anemoi.registry as mod

        importlib.reload(mod)
        assert "v1" in mod.Dataset.__module__

    def test_version_2_loads_v2(self, monkeypatch):
        monkeypatch.setenv("ANEMOI_REGISTRY_CLI_VERSION", "2")
        import anemoi.registry as mod

        importlib.reload(mod)
        assert "v2" in mod.Dataset.__module__
