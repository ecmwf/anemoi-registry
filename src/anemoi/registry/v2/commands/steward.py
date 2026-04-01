# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ..tasks import TaskCatalogueEntry
from ..utils import list_to_dict
from ..workers import run_worker
from .base import BaseCommand

LOG = logging.getLogger(__name__)


class StewardCommand(BaseCommand):
    """Run a steward worker, taking ownership of tasks and running them."""

    internal = True
    timestamp = True
    entry_class = TaskCatalogueEntry
    command = "steward"

    collection = "tasks"

    def add_arguments(self, command_parser):

        group = command_parser.add_mutually_exclusive_group()

        # --- Setup / inspection ---
        group.add_argument(
            "--setup",
            action="store_true",
            help="Set up local site (use --config URL to bootstrap, or run interactive assistant).",
        )
        # --- Direct site operations (run immediately, no catalogue check) ---
        group.add_argument(
            "--monitor-storage",
            action="store_true",
            help="Report quota/storage usage for local site. Runs immediately without checking the catalogue.",
        )
        group.add_argument(
            "--monitor-datasets",
            action="store_true",
            help="Report dataset replica status for local site. Runs immediately without checking the catalogue.",
        )
        group.add_argument(
            "--update-auxiliary",
            action="store_true",
            help="Download auxiliary files for local site. Runs immediately without checking the catalogue.",
        )
        group.add_argument(
            "--update-shared-config",
            action="store_true",
            help="Re-fetch site config from server and update the shared config dir. Runs immediately without checking the catalogue.",
        )

        # --- Catalogue task runner ---
        group.add_argument(
            "--run-task",
            nargs="*",
            metavar="K=V",
            help="Claim ownership of a queued catalogue task matching the given filters and execute it. "
            "Does nothing if no matching task is queued. Designed to be called from an ecflow job. "
            "Examples: uuid=<id> — run a specific task; "
            "action=transfer-dataset destination=lumi — run the next queued transfer to lumi; "
            "action=delete-dataset dataset=my-dataset.zarr — run the next queued delete for a dataset.",
        )

        # --- Common options ---
        command_parser.add_argument(
            "--config",
            metavar="URL_OR_FILE",
            help="Override site config: a URL (https://…/sites/<name>) or a JSON/TOML file.",
        )
        group.add_argument(
            "--dump-config",
            action="store_true",
            help="Fetch and print site config JSON (use --config URL).",
        )

        command_parser.add_argument("--dry-run", action="store_true", help="Dry run, do not actually do anything.")
        command_parser.add_argument(
            "--threads",
            type=int,
            metavar="N",
            help="Override number of transfer threads (for --run-task with action=transfer-dataset).",
        )

    def run(self, args):
        if args.setup:
            self._run_setup(args)
        elif args.dump_config:
            self._run_dump_config(args)
        elif args.monitor_storage:
            self._run_site_operation("monitor-storage", args)
        elif args.monitor_datasets:
            self._run_site_operation("monitor-datasets", args)
        elif args.update_auxiliary:
            self._run_site_operation("update-auxiliary", args)
        elif args.update_shared_config:
            self._run_update_shared_config()
        elif args.run_task is not None:
            self._run_by_filter(args)
        else:
            LOG.error("No action specified. See: anemoi-registry steward --help")

    def _run_site_operation(self, action, args):
        from ..entry.site import SiteCatalogueEntry

        site = SiteCatalogueEntry(name="local", base_url=self._resolve_config(args.config))
        if action == "monitor-storage":
            site.report_storage(dry_run=args.dry_run)
        elif action == "monitor-datasets":
            site.report_datasets(dry_run=args.dry_run)
        elif action == "update-auxiliary":
            site.update_auxiliary(dry_run=args.dry_run)

    def _resolve_config(self, config):
        """Resolve --config to a base_url string, or return None to use local bootstrap."""
        if config is None:
            return None
        if config.startswith("http://") or config.startswith("https://"):
            return config
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
        return data["base_url"]

    def _run_by_filter(self, args):
        """Resolve action from catalogue and run the appropriate worker."""
        from ..site.bootstrap import load_bootstrap
        from ..tasks import TaskCatalogueEntryList

        filters = list_to_dict(args.run_task) if args.run_task else {}
        tasks = list(TaskCatalogueEntryList(status="queued", **filters))
        if not tasks:
            LOG.info(f"No queued tasks found matching {filters}")
            return
        task = tasks[0]
        action = task.record["action"]
        LOG.info(f"Resolved action={action!r} for task {task.key}")

        # Load worker kwargs from steward.json tasks config, excluding "filter" sub-dict
        try:
            task_config = load_bootstrap().get("tasks", {}).get(action, {})
        except Exception:
            task_config = {}
        worker_kwargs = {k: v for k, v in task_config.items() if k != "filter"}

        # CLI --threads overrides config value
        if args.threads is not None:
            worker_kwargs["threads"] = args.threads

        run_worker(action, filter_tasks=filters, dry_run=args.dry_run, **worker_kwargs)

    def _run_update_shared_config(self):
        from ..site.config import fetch_and_save_shared_config

        fetch_and_save_shared_config()

    def _run_dump_config(self, args):
        import json

        if args.config:
            from ..rest import Rest

            data = Rest().get_url(self._resolve_config(args.config))
        else:
            from ..site.bootstrap import load_bootstrap

            data = load_bootstrap()

        print(json.dumps(data, indent=2))

    def _run_setup(self, args):
        if args.config:
            from ..entry.site import SiteCatalogueEntry

            SiteCatalogueEntry(name="local").setup(self._resolve_config(args.config))
        else:
            from ..site.setup_assistant import run_setup_assistant

            run_setup_assistant()


command = StewardCommand
