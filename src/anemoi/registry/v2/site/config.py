# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site config loading and fetching."""

import json
import logging
import os
from pathlib import Path

from ..rest import Rest

LOG = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Return the config directory from bootstrap."""
    from .bootstrap import BOOTSTRAP_PATH
    from .bootstrap import load_bootstrap

    bootstrap = load_bootstrap()
    config_dir = bootstrap.get("config_dir")
    if not config_dir:
        raise ValueError(f"No config_dir in {BOOTSTRAP_PATH}\n" "Run with --setup first.")
    return Path(config_dir)


def load_site_config(section: str) -> dict:
    """Load a config section from the config directory."""
    config_dir = get_config_dir()
    path = config_dir / f"{section}.json"
    if not path.exists():
        raise ValueError(f"Config not found: {path}\n" "Run with --setup first.")
    with open(path) as f:
        return json.load(f)


def fetch_and_save_configs():
    """Fetch configs from server and save as JSON files.

    1. Fetch top-level config from {base_url}/config
    2. Read site_config_path from the bootstrap section
    3. Save each config section as {key}.json in site_config_path
    """
    from .bootstrap import BOOTSTRAP_PATH
    from .bootstrap import check_group_readable
    from .bootstrap import load_bootstrap

    bootstrap = load_bootstrap()
    base_url = bootstrap.get("base_url")
    if not base_url:
        raise ValueError(f"No base_url in {BOOTSTRAP_PATH}")

    rest = Rest()

    # Step 1: Fetch top-level config (site_config_path, etc.)
    config_url = f"{base_url}/config"
    print(f"Fetching config from {config_url}")
    top_config = rest.get_url(config_url)

    bootstrap_config = top_config.get("bootstrap", {})
    site_config_path = bootstrap_config.get("site_config_path")
    if not site_config_path:
        raise ValueError("Config missing 'bootstrap.site_config_path'")

    # Canonicalise to prevent path traversal tricks
    config_dir = Path(os.path.expanduser(site_config_path)).resolve()
    config_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Fetch and save a JSON file for each config section
    saved_paths = []
    for key in top_config:
        if key == "server_url":
            continue
        section_url = f"{base_url}/config?{key}"
        print(f"Fetching {key} config from {section_url}")
        section_config = rest.get_url(section_url)
        if not section_config:
            print(f"Warning: {key} config is empty.")
            continue
        section_path = config_dir / f"{key}.json"
        with open(section_path, "w") as f:
            json.dump(section_config, f, indent=2)
        print(f"  Saved to {section_path}")
        saved_paths.append(section_path)

    # Save config_dir (canonicalised) in bootstrap
    with open(BOOTSTRAP_PATH, "w") as f:
        f.write(f'base_url = "{base_url}"\n')
        f.write(f'config_dir = "{config_dir}"\n')

    # Check group readability
    check_group_readable(config_dir)
    for p in saved_paths:
        check_group_readable(p)

    print(f"Done! Configs saved to {config_dir}/")
    if site_config_path != str(config_dir):
        print(f"  (expanded from: {site_config_path})")
