# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Manifest-driven quota status handler."""

import logging
import subprocess

from ..rest import Rest
from .parsers import COMMAND_BUILDERS
from .parsers import PARSERS

LOG = logging.getLogger(__name__)


def get_real_path(path: str) -> str:
    """Resolve symlinks to the real path (no-op for s3:// paths)."""
    import os

    if path.startswith("s3://"):
        return path
    new_path = os.path.realpath(path)
    while new_path != path:
        path = new_path
        new_path = os.path.realpath(path)
    return path


class Monitoring:
    """Runs the quota commands declared in a monitoring manifest and parses their output."""

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
        """Generate quota commands from the manifest."""
        return self.command_builder(self.quota_config)

    def get_platform_status(self) -> list[dict]:
        """Run quota commands and parse their output."""
        records: list[dict] = []
        cmds = self.get_quota_cmds()
        if not cmds:
            print(f"Warning: No quota commands generated for method '{self.method}'.")
            print("Check steward.json has the right config (e.g., 'paths' for df, 'projects' for lfs).")
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

    def report_storage(self, base_url: str, is_test: bool = False) -> None:
        """Run quota commands and POST the parsed records to ``{base_url}/resources``."""
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
