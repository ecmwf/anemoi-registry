# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site monitoring: quota reporting and replica status checking."""

import logging
import os
import subprocess
from datetime import datetime
from datetime import timezone

import tqdm

from ..rest import Rest
from .bootstrap import load_bootstrap
from .config import load_site_config
from .parsers import COMMAND_BUILDERS
from .parsers import PARSERS

LOG = logging.getLogger(__name__)


def get_real_path(path) -> str:
    """Resolve symlinks to the real path."""
    if path.startswith("s3://"):
        return path
    new_path = os.path.realpath(path)
    while new_path != path:
        path = new_path
        new_path = os.path.realpath(path)
    return path


def dataset_last_accessed(path) -> str:
    """Get the last access time of a dataset's data/.zarray file."""
    zarray_path = os.path.join(path, "data", ".zarray")
    stat_result = os.stat(zarray_path)
    dt = datetime.fromtimestamp(stat_result.st_atime, tz=timezone.utc)
    return dt.isoformat()


def load_monitoring_manifest() -> dict:
    """Load monitoring config and verify server match."""
    bootstrap = load_bootstrap()
    base_url = bootstrap.get("base_url")
    manifest = load_site_config("monitoring")

    # Verify config was fetched from the same server we're configured to use
    config_server_url = manifest.get("server_url")
    if config_server_url and base_url and not base_url.startswith(config_server_url):
        raise ValueError(
            f"Config/server mismatch!\n"
            f"  monitoring.json was fetched from: {config_server_url}\n"
            f"  site.toml base_url:               {base_url}\n"
            f"Re-run: anemoi-registry site --setup URL"
        )

    return manifest


class SiteStatus:
    """Manifest-driven quota status handler."""

    def __init__(self, manifest: dict):
        self.manifest = manifest
        quota_config = manifest.get("quota", {})
        self.method = quota_config.get("method")
        if not self.method:
            raise ValueError("No quota.method in monitoring manifest")
        if self.method not in PARSERS:
            raise ValueError(f"Unknown quota method: {self.method}. Available: {list(PARSERS.keys())}")
        self.parser = PARSERS[self.method]
        self.command_builder = COMMAND_BUILDERS[self.method]
        self.quota_config = quota_config

    def get_quota_cmds(self) -> list:
        """Generate quota commands from manifest."""
        return self.command_builder(self.quota_config)

    def get_platform_status(self) -> list[dict]:
        """Run quota commands and parse output."""
        records = []
        cmds = self.get_quota_cmds()
        if not cmds:
            print(f"Warning: No quota commands generated for method '{self.method}'.")
            print("Check monitoring.json has the right config (e.g., 'paths' for df, 'projects' for lfs).")
            return records
        for cmd in cmds:
            cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
            print(f"Running command: {cmd_str}")
            result = subprocess.run(cmd, capture_output=True, text=True, shell=isinstance(cmd, str))
            print(f"Quota command stdout:\n{result.stdout}")
            print(f"Quota command stderr:\n{result.stderr}")
            records.extend(self.parser(result.stdout))
            for r in records:
                print(f"Parsed record: {r}")
        return records

    def report_storage(self, base_url: str, is_test=False):
        """Run quota commands and POST results to the server."""
        records = self.get_platform_status()

        entry_point = f"{base_url}/resources"

        rest = Rest()
        for r in records:
            path = r["resource"].get("path", r.get("path"))
            if path:
                r["real_path"] = get_real_path(path)
            print(f"Reporting status for: {r}")
            if is_test:
                print("Test mode: not sending platform status, just printing it.")
                continue
            try:
                LOG.debug(f"POST {entry_point}")
                LOG.debug(f"Payload: {r}")
                response = rest.session.post(entry_point, json=r)
                LOG.debug(f"Response status: {response.status_code}")
                LOG.debug(f"Response headers: {response.headers}")
                rest.raise_for_status(response)
                print(f"Posted: {response.json()}")
            except Exception as e:
                print(f"Error: POST {entry_point} failed: {e}")
                raise


def datasets_status(base_url: str, is_test=False) -> list[dict]:
    """Fetch replicas for this site, check local status, and POST updates."""
    entry_point = f"{base_url}/replicas"
    rest = Rest()

    # Step 1: Get replicas for this site
    print(f"Fetching replicas from {entry_point}")
    try:
        response = rest.session.get(entry_point)
        rest.raise_for_status(response)
        replicas = response.json()
    except Exception as e:
        print(f"Error: GET {entry_point} failed: {e}")
        raise

    print(f"Found {len(replicas)} replicas for this site")

    updated = 0
    skipped = 0
    progress = tqdm.tqdm(total=len(replicas), desc="Checking replicas", unit="replica")

    for replica in replicas:
        progress.update(1)
        path = replica.get("path")
        dataset = replica.get("dataset") or replica.get("name")

        LOG.debug(f"Replica record: {replica}")

        if not path:
            print(f"Warning: Replica has no path: {replica}")
            skipped += 1
            continue

        if not dataset:
            print(f"Warning: Replica has no dataset name: {replica}")
            skipped += 1
            continue

        # Skip remote paths
        if path.startswith("s3://") or path.startswith("gs://") or path.startswith("http"):
            skipped += 1
            continue

        # Warn if local path doesn't exist
        if not os.path.exists(path):
            print(f"Warning: Replica missing: {dataset} at {path}")
            skipped += 1
            continue

        do_update = {}

        try:
            real_path = get_real_path(path)
            previous_real_path = replica.get("real_path")
            if previous_real_path != real_path:
                LOG.info(f"Replica {dataset} at {path} has changed real path from {previous_real_path} to {real_path}.")
                do_update["real_path"] = real_path
        except Exception:
            LOG.warning(f"Could not resolve real path for {dataset} at {path}. Skipping.")

        try:
            last_accessed = dataset_last_accessed(path)
            previous_last_accessed = replica.get("last_accessed")
            if previous_last_accessed != last_accessed:
                LOG.info(f"Replica {dataset} at {path} has changed last accessed time.")
                do_update["last_accessed"] = last_accessed
        except Exception:
            LOG.warning(f"Could not determine last accessed time for {dataset} at {path}. Skipping.")

        if not do_update:
            continue

        updated += 1
        payload = {
            "dataset": dataset,
            **do_update,
        }
        print(f"Updating replica: {dataset} at {path}")
        if is_test:
            print(f"  Test mode: {do_update}")
        else:
            try:
                response = rest.session.post(entry_point, json=payload)
                rest.raise_for_status(response)
                print(f"  Posted: {payload}")
                print(f"  Response: {response.json()}")
            except Exception as e:
                print(f"Error: POST {entry_point} failed: {e}")
                raise
        progress.set_postfix_str(f"{updated} updated, {skipped} skipped")

    print(f"\nDone: {updated} updated, {skipped} skipped")
