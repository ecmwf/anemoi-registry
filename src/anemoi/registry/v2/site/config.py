# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site config loading and fetching."""

import logging
from pathlib import Path

from ..rest import Rest

LOG = logging.getLogger(__name__)


def load_task_config(action: str) -> dict:
    """Load the config for a given action from steward.json tasks section."""
    from .bootstrap import BOOTSTRAP_PATH
    from .bootstrap import load_bootstrap

    bootstrap = load_bootstrap()
    config = bootstrap.get("tasks", {}).get(action)
    if config is None:
        raise ValueError(f"No tasks.{action} in {BOOTSTRAP_PATH}\nRe-run: anemoi-registry steward --setup URL")
    return config


# Keep as alias for backwards compatibility within this package
load_site_config = load_task_config


def get_config_dir() -> Path:
    """Return the shared config directory from steward.json."""
    from .bootstrap import BOOTSTRAP_PATH
    from .bootstrap import load_bootstrap

    bootstrap = load_bootstrap()
    section = bootstrap.get("tasks", {}).get("update-shared-config", {})
    config_dir = section.get("site_config_path")
    if not config_dir:
        raise ValueError(
            f"No tasks.update-shared-config.site_config_path in {BOOTSTRAP_PATH}\nRun --update-shared-config first."
        )
    return Path(config_dir)


def fetch_and_save_steward_config():
    """Fetch {steward_url}/config and merge into steward.json."""
    from .bootstrap import BOOTSTRAP_PATH
    from .bootstrap import load_bootstrap
    from .bootstrap import update_steward_settings

    bootstrap = load_bootstrap()
    steward_url = bootstrap.get("steward_url")
    if not steward_url:
        raise ValueError(f"No steward_url in {BOOTSTRAP_PATH}")

    url = f"{steward_url}/config"
    print(f"Fetching steward config from {url}")
    config = Rest().get_url(url)
    update_steward_settings(**config)
    print(f"Saved to {BOOTSTRAP_PATH}")


def fetch_and_save_shared_config():
    """Fetch shared config and write to site_config_path (needs write access)."""
    import json
    import os

    from .bootstrap import check_group_readable
    from .bootstrap import load_bootstrap

    bootstrap = load_bootstrap()
    steward_url = bootstrap.get("steward_url")
    shared_section = bootstrap.get("tasks", {}).get("update-shared-config", {})
    site_config_path = shared_section.get("site_config_path")
    if not site_config_path:
        raise ValueError("No update-shared-config.site_config_path in steward.json\nRun --setup first.")

    config_dir = Path(os.path.expanduser(site_config_path)).resolve()
    config_dir.mkdir(parents=True, exist_ok=True)

    url = f"{steward_url}/shared/config"
    print(f"Fetching shared config from {url}")
    shared_config = Rest().get_url(url)

    saved_paths = []
    for key, section_config in shared_config.items():
        section_path = config_dir / f"{key}.json"
        with open(section_path, "w") as f:
            json.dump(section_config, f, indent=2)
        print(f"  Saved to {section_path}")
        saved_paths.append(section_path)

    check_group_readable(config_dir)
    for p in saved_paths:
        check_group_readable(p)
    print(f"Done! Shared configs saved to {config_dir}/")
