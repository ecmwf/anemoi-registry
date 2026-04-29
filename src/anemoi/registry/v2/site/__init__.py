# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Site context: local steward-bootstrap config and helpers.

The :class:`Site` object wraps the steward bootstrap dict
(``~/.config/anemoi/steward.json`` or an in-process override) and exposes
all operations that act on the local site:

- factories (``from_input`` / ``from_name`` / ``from_url`` / ``from_file``
  / ``from_disk``) for resolving a site name, URL, or file path to a
  bootstrap dict;
- ``install_as_current()`` / ``current()`` for a process-wide active site;
- ``task_config(action)`` / ``monitoring_manifest()`` / ``config_dir()`` for
  reading sections of the bootstrap;
- ``setup()`` / ``fetch_and_save_steward_config()`` /
  ``fetch_and_save_shared_config()`` for first-time setup and refresh;
- ``report_storage()`` / ``report_datasets()`` / ``update_auxiliary()`` for
  the steward worker actions that operate on this host.

Note: the v2-level ``Site`` symbol (``from anemoi.registry.v2 import Site``)
is the catalogue-entry class :class:`~anemoi.registry.v2.entry.site.SiteCatalogueEntry`,
not this class. This class is the *local* site context.
"""

import json
import logging
import os
import re
import stat
from datetime import datetime
from datetime import timezone
from pathlib import Path

import tqdm

from ..rest import Rest

LOG = logging.getLogger(__name__)

BOOTSTRAP_PATH = Path(os.path.expanduser("~/.config/anemoi/steward.json"))


# ---------------------------------------------------------------------------
# Module-level helpers (used by Site and by callers that don't need a Site)
# ---------------------------------------------------------------------------


def site_name_to_url(name: str) -> str:
    """Return the canonical config URL for a given site name."""
    return f"{Rest().api_url}/sites/{name}/config"


def check_group_readable(path: Path) -> None:
    """Warn if ``path`` is not readable by group."""
    mode = path.stat().st_mode
    if path.is_dir():
        if not (mode & stat.S_IRGRP and mode & stat.S_IXGRP):
            LOG.warning(f"Directory not accessible by group: {path} (mode: {stat.filemode(mode)})")
            print(f"Warning: {path} is not group-accessible. Consider: chmod g+rx {path}")
    else:
        if not (mode & stat.S_IRGRP):
            LOG.warning(f"File not readable by group: {path} (mode: {stat.filemode(mode)})")
            print(f"Warning: {path} is not group-readable. Consider: chmod g+r {path}")


def get_real_path(path: str) -> str:
    """Resolve symlinks to the real path (no-op for s3:// paths)."""
    if path.startswith("s3://"):
        return path
    new_path = os.path.realpath(path)
    while new_path != path:
        path = new_path
        new_path = os.path.realpath(path)
    return path


def dataset_last_accessed(path: str) -> str:
    """Return the ISO last-access timestamp of a dataset's ``data/.zarray`` file."""
    zarray_path = os.path.join(path, "data", ".zarray")
    stat_result = os.stat(zarray_path)
    dt = datetime.fromtimestamp(stat_result.st_atime, tz=timezone.utc)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Site — local bootstrap context + actions
# ---------------------------------------------------------------------------


class Site:
    """Local site context.

    Wraps the steward bootstrap dict and exposes all operations that act
    on the local site. Construct via the ``from_*`` factories and (for the
    run-time current site) install with :py:meth:`install_as_current`.
    """

    _current: "Site | None" = None

    def __init__(self, data: dict):
        self.data = data

    # -------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------

    @classmethod
    def from_input(cls, config: str) -> "Site":
        """Auto-detect a plain site name, URL, or local file path and build a :class:`Site`."""
        if config.startswith(("http://", "https://")):
            return cls.from_url(config)
        if not Path(config).exists():
            return cls.from_name(config)
        return cls.from_file(config)

    @classmethod
    def from_name(cls, name: str) -> "Site":
        """Resolve a bare site name against the registry server."""
        url = site_name_to_url(name)
        LOG.info(f"Resolving site name {name!r} to config URL: {url}")
        data = Rest().get_url(url)
        data.setdefault("name", name)
        return cls(data)

    @classmethod
    def from_url(cls, url: str) -> "Site":
        """Fetch site config from a full URL (extracts ``name`` from ``.../sites/<name>/config``)."""
        data = Rest().get_url(url)
        m = re.search(r"/sites/([^/]+)/config", url)
        if m:
            data.setdefault("name", m.group(1))
        return cls(data)

    @classmethod
    def from_file(cls, path) -> "Site":
        """Load site config from a local JSON or TOML file."""
        path = Path(path)
        if path.suffix == ".toml":
            import tomllib

            with open(path, "rb") as f:
                return cls(tomllib.load(f))
        with open(path) as f:
            return cls(json.load(f))

    @classmethod
    def from_disk(cls) -> "Site":
        """Load the persisted bootstrap from ``~/.config/anemoi/steward.json``."""
        if not BOOTSTRAP_PATH.exists():
            raise ValueError(
                f"Steward config not found: {BOOTSTRAP_PATH}\n"
                "Run: anemoi-registry steward --setup https://server/api/v1/sites/<site>"
            )
        with open(BOOTSTRAP_PATH) as f:
            return cls(json.load(f))

    # -------------------------------------------------------------------
    # Process-wide current site
    # -------------------------------------------------------------------

    @classmethod
    def current(cls) -> "Site":
        """Return the currently-installed site, falling back to the on-disk bootstrap."""
        if cls._current is None:
            cls._current = cls.from_disk()
        return cls._current

    def install_as_current(self) -> None:
        """Install ``self`` as the process-wide current site."""
        type(self)._current = self

    # -------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------

    @property
    def name(self) -> str | None:
        return self.data.get("name")

    @property
    def site_url(self) -> str | None:
        return self.data.get("site_url")

    @property
    def base_url(self) -> str:
        url = self.site_url
        if not url:
            raise ValueError(f"No site_url in {BOOTSTRAP_PATH}. Run: anemoi-registry steward --setup URL")
        return url

    # -------------------------------------------------------------------
    # Config accessors
    # -------------------------------------------------------------------

    def task_config(self, action: str) -> dict:
        """Return ``tasks.<action>`` from the bootstrap (raises if missing)."""
        config = self.data.get("tasks", {}).get(action)
        if config is None:
            raise ValueError(f"No tasks.{action} in {BOOTSTRAP_PATH}\nRe-run: anemoi-registry steward --setup URL")
        return config

    def task_config_or_empty(self, action: str) -> dict:
        """Like :py:meth:`task_config` but returns ``{}`` when missing."""
        return self.data.get("tasks", {}).get(action, {})

    def config_dir(self) -> Path:
        """Return the shared config directory from ``tasks.update-shared-config``."""
        section = self.data.get("tasks", {}).get("update-shared-config", {})
        path = section.get("site_config_path")
        if not path:
            raise ValueError(
                f"No tasks.update-shared-config.site_config_path in {BOOTSTRAP_PATH}\n"
                "Run --update-shared-config first."
            )
        return Path(path)

    def monitoring_manifest(self) -> dict:
        """Return the ``tasks.monitor-storage`` manifest, validating server consistency."""
        site_url = self.site_url
        manifest = self.data.get("tasks", {}).get("monitor-storage")
        if not manifest:
            raise ValueError("No tasks.monitor-storage in site config\nRe-run: anemoi-registry steward --setup URL")

        config_server_url = self.data.get("server_url")
        if config_server_url and site_url and not site_url.startswith(config_server_url):
            raise ValueError(
                f"Config/server mismatch!\n"
                f"  steward.json server_url: {config_server_url}\n"
                f"  steward.json site_url:   {site_url}\n"
                f"Re-run: anemoi-registry steward --setup URL"
            )
        return manifest

    # -------------------------------------------------------------------
    # Catalogue queries (delegate to entry classes)
    # -------------------------------------------------------------------

    def replicas(self):
        """Replicas registered for this site (catalogue query)."""
        if not self.name:
            raise ValueError("Site has no name; cannot query replicas")
        from ..entry.replica import ReplicaCatalogueEntryList

        return ReplicaCatalogueEntryList(site=self.name)

    def resources(self) -> list[dict]:
        """Resource/quota records for this site fetched from the API."""
        rest = Rest()
        url = f"{self.base_url}/resources"
        response = rest.session.get(url)
        rest.raise_for_status(response)
        return response.json()

    # -------------------------------------------------------------------
    # Persistence (writes ~/.config/anemoi/steward.json)
    # -------------------------------------------------------------------

    @staticmethod
    def _update_steward_settings(**kwargs) -> None:
        """Partial-update steward.json (preserves existing keys)."""
        existing: dict = {}
        if BOOTSTRAP_PATH.exists():
            with open(BOOTSTRAP_PATH) as f:
                existing = json.load(f)
        existing.update(kwargs)
        BOOTSTRAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BOOTSTRAP_PATH, "w") as f:
            json.dump(existing, f, indent=2, sort_keys=True)

    @classmethod
    def setup(cls, site_url: str) -> "Site":
        """First-time bootstrap: persist ``site_url``, validate server, fetch full task config.

        Returns the freshly-loaded :class:`Site` (also installed as current).
        """
        site_url = site_url.rstrip("/")
        if site_url.startswith("http://"):
            site_url = site_url.replace("http://", "https://", 1)
            print(f"Note: Upgraded to HTTPS: {site_url}")

        cls._update_steward_settings(site_url=site_url)
        print(f"Written to {BOOTSTRAP_PATH}")
        print(f"  site_url = {site_url}")

        site = cls.from_disk()
        site.install_as_current()

        print()
        print("Checking server setup...")
        if not site.check_server_setup():
            print("Server check failed. Fix the errors above before continuing.")
            raise SystemExit(1)

        print()
        print("Fetching steward config from server...")
        site.fetch_and_save_steward_config()

        site = cls.from_disk()
        site.install_as_current()
        return site

    def fetch_and_save_steward_config(self) -> None:
        """Fetch ``{site_url}/config`` and merge it into ``steward.json``."""
        site_url = self.site_url
        if not site_url:
            raise ValueError(f"No site_url in {BOOTSTRAP_PATH}")
        url = f"{site_url}/config"
        print(f"Fetching steward config from {url}")
        config = Rest().get_url(url)
        self._update_steward_settings(**config)
        print(f"Saved to {BOOTSTRAP_PATH}")

    def fetch_and_save_shared_config(self, dry_run: bool = False) -> None:
        """Write the shared config sections from ``tasks.update-shared-config`` to disk."""
        shared_section = self.data.get("tasks", {}).get("update-shared-config", {})
        site_config_path = shared_section.get("site_config_path")
        if not site_config_path:
            raise ValueError("No update-shared-config.site_config_path in site config\nRun --setup first.")

        config_dir = Path(os.path.expanduser(site_config_path)).resolve()

        # Write each sub-key (except site_config_path itself) as a separate JSON file.
        saved_paths: list[Path] = []
        for key, section_config in shared_section.items():
            if key == "site_config_path":
                continue
            section_path = config_dir / f"{key}.json"
            if dry_run:
                print(f"  Dry run: would save {section_path}")
                continue
            config_dir.mkdir(parents=True, exist_ok=True)
            with open(section_path, "w") as f:
                json.dump(section_config, f, indent=2)
            print(f"  Saved to {section_path}")
            saved_paths.append(section_path)

        check_group_readable(config_dir)
        for p in saved_paths:
            check_group_readable(p)
        print(f"Done! Shared configs saved to {config_dir}/")

    def check_server_setup(self) -> bool:
        """Fetch ``/config`` and report what tasks are available. Returns ``True`` if OK."""
        site_url = self.site_url
        if not site_url:
            raise ValueError(f"No site_url in {BOOTSTRAP_PATH}")

        rest = Rest()
        errors: list[str] = []
        warnings: list[str] = []

        config_url = f"{site_url}/config"
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
                from .parsers import PARSERS

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

        print(f"\n   POST resources : {site_url}/resources")
        print(f"   POST replicas  : {site_url}/replicas")

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
        print("\nServer setup has issues. Please fix the errors above.")
        return False

    # -------------------------------------------------------------------
    # Steward worker actions for this site
    # -------------------------------------------------------------------

    def report_storage(self, dry_run: bool = False) -> None:
        """Run quota commands and POST results to the server."""
        from .monitoring import Monitoring

        manifest = self.monitoring_manifest()
        Monitoring(manifest).report_storage(self.base_url, is_test=dry_run)

    def report_datasets(self, dry_run: bool = False) -> None:
        """Check replica status locally and POST updates to the server."""
        entry_point = f"{self.base_url}/replicas"
        rest = Rest()

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
            if path.startswith("s3://") or path.startswith("gs://") or path.startswith("http"):
                skipped += 1
                continue
            if not os.path.exists(path):
                print(f"Warning: Replica missing: {dataset} at {path}")
                skipped += 1
                continue

            do_update: dict = {}

            try:
                real_path = get_real_path(path)
                previous_real_path = replica.get("real_path")
                if previous_real_path != real_path:
                    LOG.info(
                        f"Replica {dataset} at {path} has changed real path from "
                        f"{previous_real_path} to {real_path}."
                    )
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
            payload = {"dataset": dataset, **do_update}
            print(f"Updating replica: {dataset} at {path}")
            if dry_run:
                print(f"  Dry run: {do_update}")
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

    def update_auxiliary(self, dry_run: bool = False) -> None:
        """Download auxiliary files specified in ``tasks.update-auxiliary``."""
        from anemoi.utils.remote import transfer

        auxiliary = self.task_config_or_empty("update-auxiliary")
        base_path = Path(auxiliary.get("path", "."))
        elements = auxiliary.get("elements", [])
        if not elements:
            print("Warning: No elements in auxiliary config.")
            return

        for elem in elements:
            source = elem["source"]
            target_dir = base_path / elem["target_dir"]
            filename = os.path.basename(source)
            target = target_dir / filename

            print(f"Transferring {source}")
            print(f"  -> {target}")

            if dry_run:
                print("  Dry run: skipping transfer")
                continue

            target_dir.mkdir(parents=True, exist_ok=True)
            transfer(source, str(target), resume=True)
            print("  Done")

    def __repr__(self) -> str:
        return f"Site(name={self.name!r})"


__all__ = [
    "BOOTSTRAP_PATH",
    "Site",
    "check_group_readable",
    "dataset_last_accessed",
    "get_real_path",
    "site_name_to_url",
]
