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
            help="Update local auxiliary files, shared config, and dataset metadata.",
            description=(
                "Run one or more local update operations. "
                "With no flags, all updates are run: auxiliary files, shared config, and dataset metadata. "
                "Use --auxiliary, --shared-config, or --datasets to run a specific subset."
            ),
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
            from ..site import Site

            Site.from_input(args.site).install_as_current()

        if sub == "config":
            self._run_dump_config()

        elif sub == "monitor":
            from ..site import Site

            site = Site.current()
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
                self._run_update_shared_config(args)
            if args.datasets or do_all:
                self._run_update_datasets(args)

        elif sub == "run-task":
            self._run_by_filter(args)

        elif sub == "release":
            self._run_release(args)

    # --- Helpers ---

    def _run_setup(self, args):
        from ..site import Site

        if args.dry_run:
            LOG.info(f"Would set up bootstrap config from: {args.site}")
            return
        Site.setup(args.site)

    def _run_dump_config(self):
        import json

        from ..site import Site

        print(json.dumps(Site.current().data, indent=2))

    def _run_update_auxiliary(self, args):
        from ..site import Site

        Site.current().update_auxiliary(dry_run=args.dry_run)

    def _run_update_shared_config(self, args):
        from ..site import Site

        Site.current().fetch_and_save_shared_config(dry_run=args.dry_run)

    def _run_update_datasets(self, args):
        from ..commands.update import zarr_file_from_catalogue
        from ..site import Site

        def _error(message):
            LOG.error(message)

        site = Site.current()
        for replica in site.replicas():
            path = replica.path
            if not path:
                LOG.warning(f"No path for replica {replica.dataset_name!r}, skipping.")
                continue
            LOG.info(f"Updating {replica.dataset_name!r} at {path}")
            zarr_file_from_catalogue(path, dry_run=args.dry_run, ignore=True, _error=_error)

    def _run_by_filter(self, args):
        """Resolve action from catalogue and run the appropriate worker."""
        from ..site import Site
        from ..tasks import TaskCatalogueEntryList

        filters = list_to_dict(args.filters) if args.filters else {}
        tasks = list(TaskCatalogueEntryList(status="queued", **filters))
        if not tasks:
            LOG.info(f"No queued tasks found matching {filters}")
            return
        task = tasks[0]
        action = task.record["action"]
        LOG.info(f"Resolved action={action!r} for task {task.key}")

        site = Site.current()
        site_name = site.name

        # Sanity: when a uuid is given, the picked task must target this site.
        if site_name and "uuid" in filters:
            if action == "transfer-dataset":
                assert task.record.get("destination") == site_name, (
                    f"Task {task.key} destination={task.record.get('destination')!r} "
                    f"does not match site {site_name!r}"
                )
            elif action == "delete-dataset":
                assert task.record.get("location") == site_name, (
                    f"Task {task.key} location={task.record.get('location')!r} " f"does not match site {site_name!r}"
                )

        worker_kwargs = {k: v for k, v in site.task_config_or_empty(action).items() if k != "filter"}

        # Site is implicit — fill in destination/platform from the resolved
        # bootstrap name (already extracted in _apply_config_override).
        if site_name:
            if action == "transfer-dataset":
                worker_kwargs.setdefault("destination", site_name)
            elif action == "delete-dataset":
                worker_kwargs.setdefault("location", site_name)

        if args.threads is not None:
            worker_kwargs["threads"] = args.threads

        run_worker(action, filter_tasks=filters, dry_run=args.dry_run, **worker_kwargs)


command = StewardCommand
