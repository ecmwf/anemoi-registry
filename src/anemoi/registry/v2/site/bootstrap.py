# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Bootstrap configuration for site setup."""

import json
import logging
import os
import stat
from pathlib import Path

from ..rest import Rest
from .config import fetch_and_save_steward_config

LOG = logging.getLogger(__name__)

BOOTSTRAP_PATH = Path(os.path.expanduser("~/.config/anemoi/steward.json"))


def check_group_readable(path: Path):
    """Warn if path is not readable by group."""
    mode = path.stat().st_mode
    if path.is_dir():
        if not (mode & stat.S_IRGRP and mode & stat.S_IXGRP):
            LOG.warning(f"Directory not accessible by group: {path} (mode: {stat.filemode(mode)})")
            print(f"Warning: {path} is not group-accessible. Consider: chmod g+rx {path}")
    else:
        if not (mode & stat.S_IRGRP):
            LOG.warning(f"File not readable by group: {path} (mode: {stat.filemode(mode)})")
            print(f"Warning: {path} is not group-readable. Consider: chmod g+r {path}")


def load_bootstrap() -> dict:
    """Load config from ~/.config/anemoi/steward.json."""
    if not BOOTSTRAP_PATH.exists():
        raise ValueError(
            f"Steward config not found: {BOOTSTRAP_PATH}\n"
            "Run: anemoi-registry steward --setup https://server/api/v1/sites/<site>"
        )
    with open(BOOTSTRAP_PATH) as f:
        return json.load(f)


def update_steward_settings(**kwargs):
    """Partial-update steward.json with the given key=value pairs.

    Existing keys not mentioned in kwargs are preserved.
    """
    existing = {}
    if BOOTSTRAP_PATH.exists():
        with open(BOOTSTRAP_PATH) as f:
            existing = json.load(f)

    existing.update(kwargs)

    BOOTSTRAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BOOTSTRAP_PATH, "w") as f:
        json.dump(existing, f, indent=2)


def setup_bootstrap(steward_url: str):
    """Write steward_url to steward.json, check server, fetch user configs."""
    steward_url = steward_url.rstrip("/")

    if steward_url.startswith("http://"):
        steward_url = steward_url.replace("http://", "https://", 1)
        print(f"Note: Upgraded to HTTPS: {steward_url}")

    update_steward_settings(steward_url=steward_url)
    print(f"Written to {BOOTSTRAP_PATH}")
    print(f"  steward_url = {steward_url}")

    print()
    print("Checking server setup...")
    success = check_server_setup()
    if not success:
        print("Server check failed. Fix the errors above before continuing.")
        raise SystemExit(1)

    print()
    print("Fetching steward config from server...")
    fetch_and_save_steward_config()


def check_server_setup():
    """Validate that the server endpoints are correctly configured."""
    from .parsers import PARSERS

    bootstrap = load_bootstrap()
    steward_url = bootstrap.get("steward_url")
    if not steward_url:
        raise ValueError(f"No steward_url in {BOOTSTRAP_PATH}")

    rest = Rest()
    errors = []
    warnings = []

    # Check 1: Fetch top-level config
    print("1. Checking top-level config...")
    config_url = f"{steward_url}/config"
    top_config = None
    try:
        top_config = rest.get_url(config_url)
        print(f"   OK: Fetched from {config_url}")
    except Exception as e:
        errors.append(f"Failed to fetch config: {e}")
        print(f"   FAIL: {e}")

    if top_config:
        bootstrap_config = top_config.get("bootstrap", {})
        for field in ("site_config_path", "site_config_entry_point"):
            if field in bootstrap_config:
                print(f"   OK: Has 'bootstrap.{field}': {bootstrap_config[field]!r:.60}")
            else:
                errors.append(f"Config missing required field: bootstrap.{field}")
                print(f"   FAIL: Missing 'bootstrap.{field}'")

    # Check 1b: Fetch monitoring config
    print("\n1b. Checking monitoring config...")
    monitoring_url = f"{steward_url}/config?monitoring"
    manifest = None
    try:
        manifest = rest.get_url(monitoring_url)
        print(f"   OK: Fetched from {monitoring_url}")
    except Exception as e:
        errors.append(f"Failed to fetch monitoring config: {e}")
        print(f"   FAIL: {e}")

    if manifest:
        expected_keys = {"quota", "server_url"}
        actual_keys = set(manifest.keys())
        extra_keys = actual_keys - expected_keys
        if extra_keys:
            warnings.append(f"Unexpected keys in monitoring config: {extra_keys}")
            print(f"   WARN: Unexpected keys: {extra_keys}")

        # Validate quota config
        quota = manifest.get("quota", {})
        if "method" in quota:
            method = quota["method"]
            if method in PARSERS:
                print(f"   OK: quota.method '{method}' is supported")
                if method in ("df", "lfs-project"):
                    if "paths" in quota and quota["paths"]:
                        print(f"   OK: quota.paths has {len(quota['paths'])} entries")
                    else:
                        errors.append(f"Method '{method}' requires 'paths' array in quota config")
                        print(f"   FAIL: Method '{method}' requires 'paths' array")
                elif method in ("lfs", "lfs-columnar", "lumi-quota", "jutil"):
                    if "projects" in quota and quota["projects"]:
                        print(f"   OK: quota.projects has {len(quota['projects'])} entries")
                    else:
                        errors.append(f"Method '{method}' requires 'projects' array in quota config")
                        print(f"   FAIL: Method '{method}' requires 'projects' array")
            else:
                errors.append(f"Unknown quota.method: {method}")
                print(f"   FAIL: quota.method '{method}' not in {list(PARSERS.keys())}")
        else:
            errors.append("Manifest missing quota.method")
            print("   FAIL: Missing 'quota.method'")

    # Check 2: Fetch datasets config
    print("\n2. Checking datasets config...")
    datasets_url = f"{steward_url}/config?datasets"
    try:
        datasets_config = rest.get_url(datasets_url)
        print(f"   OK: Fetched from {datasets_url}")
        if datasets_config:
            print(f"   OK: Keys: {list(datasets_config.keys())}")
        else:
            warnings.append("Datasets config is empty ({})")
            print("   WARN: Datasets config is empty!")
    except Exception as e:
        errors.append(f"Failed to fetch datasets config: {e}")
        print(f"   FAIL: {e}")

    # Check 3: Validate site_config_path
    print("\n3. Checking site_config_path...")
    bootstrap_config = top_config.get("bootstrap", {}) if top_config else {}
    if "site_config_path" in bootstrap_config:
        raw_path = bootstrap_config["site_config_path"]
        config_path = Path(os.path.expanduser(raw_path))
        if raw_path != str(config_path):
            print(f"   Expanded: {raw_path} -> {config_path}")
        if config_path.exists():
            print(f"   OK: Path exists: {config_path}")
            if os.access(config_path, os.W_OK):
                print("   OK: Path is writable")
            else:
                warnings.append(f"Path not writable: {config_path}")
                print("   WARN: Path not writable (may need different user)")
        else:
            parent = config_path.parent
            if parent.exists() and os.access(parent, os.W_OK):
                print("   WARN: Path doesn't exist but parent is writable (will be created)")
            else:
                warnings.append(f"Path doesn't exist and parent not writable: {config_path}")
                print(f"   WARN: Path doesn't exist: {config_path}")
    else:
        print("   Skipped (no site_config_path)")

    # Check 4: Show derived endpoints
    print("\n4. Derived endpoints (from base_url)...")
    print(f"   POST resources: {steward_url}/resources")
    print(f"   POST replicas: {steward_url}/replicas")

    # Summary
    print("\nSummary:")
    if errors:
        print(f"   {len(errors)} error(s)")
        for e in errors:
            print(f"     - {e}")
    else:
        print("   No errors")

    if warnings:
        print(f"   {len(warnings)} warning(s)")
        for w in warnings:
            print(f"     - {w}")

    if not errors:
        print("\nServer setup looks good!")
        return True
    else:
        print("\nServer setup has issues. Please fix the errors above.")
        return False
