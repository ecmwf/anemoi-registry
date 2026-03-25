# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Quota output parsers and command builders for various HPC platforms."""

import csv
import io
import json
import logging
import os
import re
from datetime import datetime
from datetime import timezone

LOG = logging.getLogger(__name__)


def parse_size(s: str, none: str = None) -> int:
    """Parse a human-readable size string into bytes."""
    if s == none:
        return None
    units = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    s = s.strip()
    if s[-1] in units:
        return int(float(s[:-1]) * units[s[-1]])
    return int(s)


def parse_lfs(output: str) -> list[dict]:
    """Parse standard lfs quota verbose output."""

    def to_int(s):
        return int(s.rstrip("*")) if s not in ("-", "") else 0

    project_id = None
    records = []
    lines = output.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"Disk quotas for prj (\d+)", lines[i])
        if m:
            project_id = int(m.group(1))

        parts = lines[i].split()
        if parts and parts[0].startswith("/"):
            mount_point = parts[0]
            data_parts = parts[1:]
            if not data_parts and i + 1 < len(lines):
                i += 1
                data_parts = lines[i].split()
            if len(data_parts) >= 8:
                used_kb, soft_kb, hard_kb = data_parts[0], data_parts[1], data_parts[2]
                used_inodes, soft_inodes, hard_inodes = data_parts[4], data_parts[5], data_parts[6]
                records.append(
                    {
                        "path": mount_point,
                        "resource": {"project": project_id, "path": mount_point},
                        "bytes": to_int(used_kb) * 1024,
                        "bytes_quota": (to_int(soft_kb) or to_int(hard_kb)) * 1024,
                        "objects": to_int(used_inodes),
                        "objects_quota": to_int(soft_inodes) or to_int(hard_inodes),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
        i += 1
    return records


def parse_lfs_columnar(output: str) -> list[dict]:
    """Parse lfs quota columnar output (with --mount-point etc.)."""
    records = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 7 and parts[0].startswith("/"):
            mount_point, used_kb, soft_kb, hard_kb, used_inodes, soft_inodes, hard_inodes = parts
            records.append(
                {
                    "path": mount_point,
                    "resource": {"path": mount_point},
                    "bytes": int(used_kb) * 1024,
                    "bytes_quota": (int(soft_kb) or int(hard_kb)) * 1024,
                    "objects": int(used_inodes),
                    "objects_quota": int(soft_inodes) or int(hard_inodes),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    return records


def parse_lumi_quota(output: str) -> list[dict]:
    """Parse lumi-quota output."""
    project = None
    filesystem = None
    records = []
    for line in output.splitlines():
        m = re.match(r"Project:\s+(\S+)", line)
        if m:
            project = m.group(1)
            continue
        m = re.match(r"Project is hosted on\s+(\S+)", line)
        if m:
            filesystem = m.group(1)
            continue
        parts = line.split()
        if len(parts) == 3 and parts[0].startswith("/"):
            mount_point = parts[0]
            used_str, max_str = parts[1].split("/")
            used_bytes = parse_size(used_str)
            max_bytes = parse_size(max_str)
            used_inodes_str, max_inodes_str = parts[2].split("/")
            used_inodes = parse_size(used_inodes_str)
            max_inodes = parse_size(max_inodes_str)
            records.append(
                {
                    "path": mount_point,
                    "resource": {"path": mount_point, "project": project},
                    "bytes": used_bytes,
                    "bytes_quota": max_bytes,
                    "objects": used_inodes,
                    "objects_quota": max_inodes,
                    "extra": {"filesystem": filesystem},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    return records


def parse_cindata(output: str) -> list[dict]:
    """Parse Leonardo cindata CSV output."""
    records = []
    reader = csv.DictReader(io.StringIO(output))
    for row in reader:
        areakbused = row.get("areakbused", "").strip()
        if not areakbused:
            continue
        path = row["areadescr"]
        records.append(
            {
                "path": path,
                "resource": {"path": path, "project": row["groupname"]},
                "bytes": int(areakbused) * 1024,
                "bytes_quota": int(row["areakbmax"]) * 1024,
                "objects": int(row["areainused"]),
                "objects_quota": int(row["areainmax"]) or None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    return records


def parse_jutil(output: str) -> list[dict]:
    """Parse Jupiter jutil JSON output."""

    def kb(s):
        return int(s.removesuffix("KB")) * 1024

    records = []
    for entry in json.loads(output):
        try:
            records.append(
                {
                    "path": entry["project-dir"],
                    "resource": {"path": entry["project-dir"], "project": entry["project"]},
                    "bytes": kb(entry["data-usage"]),
                    "bytes_quota": kb(entry["data-soft-limit"]) or kb(entry["data-hard-limit"]),
                    "objects": int(entry["inode-usage"]),
                    "objects_quota": int(entry["inode-soft-limit"]) or int(entry["inode-hard-limit"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "extra": entry,
                }
            )
        except KeyError as e:
            LOG.warning(f"Missing expected key {e} in jutil output entry: {entry}")
    return records


def parse_df(output: str) -> list[dict]:
    """Parse df -Pk output (POSIX format, kilobytes)."""
    records = []
    lines = output.strip().splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 6:
            filesystem = parts[0]
            total_kb = int(parts[1])
            used_kb = int(parts[2])
            mount_point = parts[5]
            records.append(
                {
                    "path": mount_point,
                    "resource": {"path": mount_point, "filesystem": filesystem},
                    "bytes": used_kb * 1024,
                    "bytes_quota": total_kb * 1024,
                    "objects": 0,
                    "objects_quota": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
    return records


def parse_bsc_quota(output: str) -> list[dict]:
    """Parse bsc_quota -u KB output."""
    # Strip ANSI escape codes (colours, bold, hyperlinks, etc.)
    output = re.sub(r"\x1b\][^\x1b]*\x1b\\", "", output)  # OSC sequences (hyperlinks)
    output = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", output)  # CSI sequences (colours)

    # Join continuation lines (long rows may wrap after the "|")
    lines = output.splitlines()
    joined = []
    for line in lines:
        if joined and joined[-1].rstrip().endswith("|"):
            joined[-1] += " " + line
        else:
            joined.append(line)

    records = []
    for line in joined:
        parts = line.split()
        # Skip non-data lines (headers, blank, informational)
        if len(parts) < 12 or "|" not in parts:
            continue
        try:
            pipe_idx = parts.index("|")
            filesystem = parts[0]
            usage_kb = float(parts[2])
            quota_kb = float(parts[4])
            limit_kb = float(parts[6])
            files = int(parts[pipe_idx + 1])
            records.append(
                {
                    "path": filesystem,
                    "resource": {"path": filesystem},
                    "bytes": int(usage_kb * 1024),
                    "bytes_quota": int((quota_kb or limit_kb) * 1024),
                    "objects": files,
                    "objects_quota": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except (ValueError, IndexError):
            continue
    return records


PARSERS = {
    "lfs": parse_lfs,
    "lfs-columnar": parse_lfs_columnar,
    "lumi-quota": parse_lumi_quota,
    "cindata": parse_cindata,
    "jutil": parse_jutil,
    "df": parse_df,
    "bsc_quota": parse_bsc_quota,
}


# ---- Command builders ----

def expand_path(path: str) -> str:
    """Expand ~ and $ENV_VAR in paths."""
    return os.path.expandvars(os.path.expanduser(path))


def build_commands_lfs(quota_config: dict) -> list[str]:
    """Build lfs quota commands (verbose output)."""
    commands = []
    for p in quota_config.get("projects", []):
        project_id = p["id"]
        path = p["path"]
        commands.append(f"lfs quota -p {project_id} {path}")
    return commands


def build_commands_lfs_columnar(quota_config: dict) -> list[list[str]]:
    """Build lfs quota commands (columnar output)."""
    commands = []
    for p in quota_config.get("projects", []):
        project_id = p["id"]
        path = p["path"]
        cmd = ["lfs", "quota", "-p", str(project_id)]
        cmd += [
            "--mount-point",
            "--blocks",
            "--block-softlimit",
            "--block-hardlimit",
            "--inodes",
            "--inode-softlimit",
            "--inode-hardlimit",
            path,
        ]
        commands.append(cmd)
    return commands


def build_commands_lumi_quota(quota_config: dict) -> list[list[str]]:
    """Build lumi-quota commands."""
    commands = []
    for p in quota_config.get("projects", []):
        project = p["name"]
        commands.append(["lumi-quota", "-p", project])
    return commands


def build_commands_cindata(quota_config: dict) -> list[list[str]]:
    """Build cindata command."""
    return [["cindata", "-f", "0"]]


def build_commands_jutil(quota_config: dict) -> list[str]:
    """Build jutil commands."""
    commands = []
    for p in quota_config.get("projects", []):
        project = p["name"]
        commands.append(f"jutil project dataquota --project {project} -o json -U KB")
    return commands


def build_commands_df(quota_config: dict) -> list[list[str]]:
    """Build df commands."""
    commands = []
    for p in quota_config.get("paths", []):
        path = expand_path(p["path"])
        commands.append(["df", "-Pk", path])
    return commands


def build_commands_bsc_quota(quota_config: dict) -> list[list[str]]:
    """Build bsc_quota command."""
    return [["bsc_quota", "-u", "KB"]]


COMMAND_BUILDERS = {
    "lfs": build_commands_lfs,
    "lfs-columnar": build_commands_lfs_columnar,
    "lumi-quota": build_commands_lumi_quota,
    "cindata": build_commands_cindata,
    "jutil": build_commands_jutil,
    "df": build_commands_df,
    "bsc_quota": build_commands_bsc_quota,
}
