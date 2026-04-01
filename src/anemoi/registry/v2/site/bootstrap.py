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
    """Fetch /config and report what tasks are available."""
    from .parsers import PARSERS

    bootstrap = load_bootstrap()
    steward_url = bootstrap.get("steward_url")
    if not steward_url:
        raise ValueError(f"No steward_url in {BOOTSTRAP_PATH}")

    rest = Rest()
    errors = []
    warnings = []

    # Fetch the steward config endpoint
    config_url = f"{steward_url}/config"
    print(f"Checking {config_url} ...")
    config = None
    try:
        config = rest.get_url(config_url)
        print(f"   OK: Fetched from {config_url}")
    except Exception as e:
        errors.append(f"Failed to fetch steward config: {e}")
        print(f"   FAIL: {e}")

    if config:
        server_url = config.get("server_url")
        if server_url:
            print(f"   OK: server_url = {server_url}")
        else:
            errors.append("Missing 'server_url' in steward config")
            print("   FAIL: Missing 'server_url'")

        tasks = config.get("tasks", {})
        if tasks:
            print(f"   OK: Tasks: {list(tasks.keys())}")
        else:
            warnings.append("No tasks in steward config")
            print("   WARN: No tasks found")

        # Validate monitor-storage quota method if present
        monitor_storage = tasks.get("monitor-storage", {})
        quota = monitor_storage.get("quota", {})
        method = quota.get("method")
        if method:
            if method in PARSERS:
                print(f"   OK: monitor-storage quota.method '{method}' is supported")
            else:
                errors.append(f"monitor-storage quota.method '{method}' not in {list(PARSERS.keys())}")
                print(f"   FAIL: Unsupported quota.method '{method}'")

        # Check update-shared-config path if present
        shared = tasks.get("update-shared-config", {})
        site_config_path = shared.get("site_config_path")
        if site_config_path:
            config_path = Path(os.path.expanduser(site_config_path))
            if config_path.exists():
                print(f"   OK: update-shared-config.site_config_path exists: {config_path}")
            else:
                warnings.append(f"update-shared-config.site_config_path does not exist: {config_path}")
                print(f"   WARN: Path does not exist (will be created): {config_path}")

    print(f"\n   POST resources : {steward_url}/resources")
    print(f"   POST replicas  : {steward_url}/replicas")

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
