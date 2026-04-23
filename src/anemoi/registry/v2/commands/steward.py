# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import argparse
import logging

from ..tasks import TaskCatalogueEntry
from ..utils import list_to_dict
from ..workers import run_worker
from .base import BaseCommand

LOG = logging.getLogger(__name__)

_CONFIG_HELP = (
    "Site name (e.g. ewc) or a local JSON/TOML file. " "Optional for most subcommands if setup has already been run."
)

_DRY_RUN_HELP = "Dry run, do not actually do anything."


class StewardCommand(BaseCommand):
    """Run a steward worker, taking ownership of tasks and running them."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry
    command = "steward"

    collection = "tasks"

    def add_arguments(self, command_parser):
        # --site and --dry-run on the top-level parser: accepted before the subcommand.
        # Both are also injected into subparsers (SUPPRESS default) so they are accepted
        # after the subcommand name too, without overwriting the top-level value.
        command_parser.add_argument("--site", metavar="SITE_OR_FILE", help=_CONFIG_HELP)
        command_parser.add_argument("--dry-run", action="store_true", help=_DRY_RUN_HELP)

        # Shared parent for all subcommands except 'config' (which has no dry-run).
        _common_parent = argparse.ArgumentParser(add_help=False)
        _common_parent.add_argument("--site", metavar="SITE_OR_FILE", help=_CONFIG_HELP, default=argparse.SUPPRESS)
        _common_parent.add_argument("--dry-run", action="store_true", help=_DRY_RUN_HELP, default=argparse.SUPPRESS)

        # Separate parent for 'config' — only --site, no --dry-run.
        _site_parent = argparse.ArgumentParser(add_help=False)
        _site_parent.add_argument("--site", metavar="SITE_OR_FILE", help=_CONFIG_HELP, default=argparse.SUPPRESS)

        subparsers = command_parser.add_subparsers(dest="subcommand", required=True)

        # --- setup / config ---
        subparsers.add_parser(
            "setup",
            help="Initialise the local site bootstrap config (requires --site).",
            description="Initialise the local site bootstrap config. Requires --site SITE_OR_FILE.",
            parents=[_common_parent],
        )

        subparsers.add_parser(
            "config",
            help="Print the effective site config as JSON.",
            description="Load and print the site config (respects --site if given).",
            parents=[_site_parent],
        )

        def _sub(name, help, description, **kwargs):
            return subparsers.add_parser(name, help=help, description=description, parents=[_common_parent], **kwargs)

        # --- monitor ---
        p = _sub(
            "monitor",
            help="Report site status. Runs all checks by default.",
            description=(
                "Report storage and/or dataset replica status for the local site. "
                "Runs all checks when no flag is given."
            ),
        )
        g = p.add_argument_group()
        g.add_argument("--storage", action="store_true", help="Report quota/storage usage.")
        g.add_argument("--datasets", action="store_true", help="Report dataset replica status.")

        # --- update ---
        p = _sub(
            "update",
            help="Run local update operations. Runs all updates by default.",
            description=("Run one or more local update operations. " "Runs all updates when no flag is given."),
        )
        g = p.add_argument_group()
        g.add_argument("--auxiliary", action="store_true", help="Download auxiliary files for the local site.")
        g.add_argument(
            "--shared-config",
            action="store_true",
            help="Re-fetch site config from server and update the shared config dir.",
        )
        g.add_argument(
            "--datasets",
            action="store_true",
            help="Update zarr metadata for all local dataset replicas from the catalogue.",
        )

        # --- run-task ---
        p = _sub(
            "run-task",
            help="Claim and execute a queued catalogue task.",
            description=(
                "Claim ownership of a queued catalogue task matching the given filters and execute it. "
                "Does nothing if no matching task is queued. Designed to be called from an ecflow job."
            ),
        )
        g = p.add_argument_group()
        g.add_argument(
            "filters",
            nargs="*",
            metavar="K=V",
            help=(
                "Filter tasks by key=value pairs. "
                "Examples: uuid=<id> — run a specific task; "
                "action=transfer-dataset destination=lumi — run the next queued transfer to lumi; "
                "action=delete-dataset dataset=my-dataset.zarr — run the next queued delete."
            ),
        )
        g.add_argument(
            "--threads",
            type=int,
            metavar="N",
            help="Override number of transfer threads (for action=transfer-dataset).",
        )

        # --- release ---
        p = _sub(
            "release",
            help="Release ownership of a stalled running task.",
            description=(
                "Release the ownership of a task whose worker has stopped heartbeating. "
                "Intended for the steward housekeeping job."
            ),
        )
        g = p.add_argument_group()
        g.add_argument(
            "filters",
            nargs="*",
            metavar="K=V",
            help="Filter tasks to release by key=value pairs (typically uuid=<id>).",
        )
        g.add_argument(
            "--max-age",
            type=int,
            metavar="SECONDS",
            default=600,
            help="Only release tasks whose last heartbeat is older than this many seconds (default: 600).",
        )
        g.add_argument(
            "--force",
            action="store_true",
            help="Release regardless of status (bypass the status check).",
        )

    def run(self, args):
        sub = args.subcommand

        if sub == "setup":
            if not args.site:
                LOG.error("setup requires --config. Example: anemoi-registry steward --config ewc setup")
                return
            self._run_setup(args)
            return

        # Apply config override before all other subcommands.
        if args.site:
            self._apply_config_override(args.site)

        if sub == "config":
            self._run_dump_config()

        elif sub == "monitor":
            from ..entry.site import SiteCatalogueEntry

            site = SiteCatalogueEntry(name="local")
            do_all = not args.storage and not args.datasets
            if args.storage or do_all:
                site.report_storage(dry_run=args.dry_run)
            if args.datasets or do_all:
                site.report_datasets(dry_run=args.dry_run)

        elif sub == "update":
            do_all = not args.auxiliary and not args.shared_config and not args.datasets
            if args.auxiliary or do_all:
                self._run_update_auxiliary(args)
            if args.shared_config or do_all:
                self._run_update_shared_config()
            if args.datasets or do_all:
                self._run_update_datasets(args)

        elif sub == "run-task":
            self._run_by_filter(args)

        elif sub == "release":
            self._run_release(args)

    # --- Helpers ---

    def _site_name_to_url(self, site):
        from ..rest import Rest

        return f"{Rest().api_url}/sites/{site}/config"

    def _apply_config_override(self, config):
        """Load config from a site name, URL, or file and set it as the in-process bootstrap override."""
        from ..site.bootstrap import set_bootstrap_override

        if config.startswith("http://") or config.startswith("https://"):
            from ..rest import Rest

            data = Rest().get_url(config)
        elif not __import__("pathlib").Path(config).exists():
            # Not a URL and not an existing file — treat as a site name.
            url = self._site_name_to_url(config)
            LOG.info(f"Resolving site name '{config}' to config URL: {url}")
            from ..rest import Rest

            data = Rest().get_url(url)
        else:
            import json
            from pathlib import Path

            path = Path(config)
            if path.suffix == ".toml":
                import tomllib

                with open(path, "rb") as f:
                    data = tomllib.load(f)
            else:
                with open(path) as f:
                    data = json.load(f)
        set_bootstrap_override(data)

    def _run_setup(self, args):
        from ..site.bootstrap import setup_bootstrap

        if args.dry_run:
            LOG.info(f"Would set up bootstrap config from: {args.site}")
            return
        setup_bootstrap(args.site)

    def _run_dump_config(self):
        import json

        from ..site.bootstrap import load_bootstrap

        print(json.dumps(load_bootstrap(), indent=2))

    def _run_update_auxiliary(self, args):
        from ..entry.site import SiteCatalogueEntry

        SiteCatalogueEntry(name="local").update_auxiliary(dry_run=args.dry_run)

    def _run_update_shared_config(self):
        from ..site.config import fetch_and_save_shared_config

        fetch_and_save_shared_config()

    def _run_update_datasets(self, args):
        from ..commands.update import zarr_file_from_catalogue
        from ..entry.site import SiteCatalogueEntry

        def _error(message):
            LOG.error(message)

        site = SiteCatalogueEntry(name="local")
        for replica in site.replicas():
            path = replica.path
            if not path:
                LOG.warning(f"No path for replica {replica.dataset_name!r}, skipping.")
                continue
            LOG.info(f"Updating {replica.dataset_name!r} at {path}")
            zarr_file_from_catalogue(path, dry_run=args.dry_run, ignore=True, _error=_error)

    def _run_by_filter(self, args):
        """Resolve action from catalogue and run the appropriate worker."""
        from ..site.bootstrap import load_bootstrap
        from ..tasks import TaskCatalogueEntryList

        filters = list_to_dict(args.filters) if args.filters else {}
        tasks = list(TaskCatalogueEntryList(status="queued", **filters))
        if not tasks:
            LOG.info(f"No queued tasks found matching {filters}")
            return
        task = tasks[0]
        action = task.record["action"]
        LOG.info(f"Resolved action={action!r} for task {task.key}")

        try:
            task_config = load_bootstrap().get("tasks", {}).get(action, {})
        except Exception:
            task_config = {}
        worker_kwargs = {k: v for k, v in task_config.items() if k != "filter"}

        if args.threads is not None:
            worker_kwargs["threads"] = args.threads

        run_worker(action, filter_tasks=filters, dry_run=args.dry_run, **worker_kwargs)

    def _run_release(self, args):
        from ..workers import release_stalled

        filters = list_to_dict(args.filters) if args.filters else {}
        release_stalled(filters=filters, max_age=args.max_age, force=args.force, dry_run=args.dry_run)


command = StewardCommand
