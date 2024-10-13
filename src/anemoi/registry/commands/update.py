#!/usr/bin/env python
# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


import logging
import os
import shutil
import time

import yaml

from anemoi.registry import Dataset
from anemoi.registry.entry import CatalogueEntryNotFound

LOG = logging.getLogger(__name__)


class Update:

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):

        group = command_parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--catalogue-from-recipe", help="Update the catalogue entry from the recipe.", action="store_true"
        )

        command_parser.add_argument("--dry-run", help="Dry run.", action="store_true")
        command_parser.add_argument("--force", help="Force.", action="store_true")
        command_parser.add_argument(
            "--continue", help="Continue to the next file on error.", action="store_true", dest="continue_"
        )
        command_parser.add_argument("--workdir", help="Work directory.", default=".")

        command_parser.add_argument("paths", nargs="*", help="Paths to update.")

    def run(self, args):
        if args.catalogue_from_recipe:
            for path in args.paths:
                try:
                    self.catalogue_from_recipe(path, args)
                except Exception as e:
                    if args.continue_:
                        LOG.exception(e)
                        continue
                    raise
            return

    def _error(self, args, message):
        LOG.error(message)
        if not args.force:
            raise ValueError(message)
        LOG.error("%s", message)
        LOG.warning("Continuing with --force.")

    def catalogue_from_recipe(self, path, args):
        """
        Update the catalogue entry a recipe file.
        """

        from anemoi.datasets.create import creator_factory

        LOG.info(f"Updating catalogue entry from recipe: {path}")

        with open(path) as f:
            recipe = yaml.safe_load(f)

        if "name" not in recipe:
            self._error(args, "Recipe does not contain a 'name' field.")

        name = recipe["name"]
        base, _ = os.path.splitext(os.path.basename(path))

        if name != base:
            self._error(args, f"Recipe name '{name}' does not match file name '{path}'")

        try:
            entry = Dataset(name)
        except CatalogueEntryNotFound:
            if args.force:
                LOG.error(f"Entry not found: {name}")
                return
            raise

        if "recipe" not in entry.record["metadata"] or args.force:
            if args.dry_run:
                LOG.info("Would set recipe %s", name)
            else:
                LOG.info("Setting recipe %s", name)
                recipe["name"] = name
                entry.set_value("/metadata/recipe", recipe)

        if "variables_metadata" not in entry.record["metadata"] or args.force:

            if args.dry_run:
                LOG.info("Would set `variables_metadata` %s", name)
            else:

                dir = os.path.join(args.workdir, f"anemoi-registry-commands-update-{time.time()}")
                os.makedirs(dir)

                try:
                    tmp = os.path.join(dir, "tmp.zarr")

                    c = creator_factory("init", config=path, path=tmp, overwrite=True)
                    c.run()

                    with open(f"{tmp}/.zattrs") as f:
                        variables_metadata = yaml.safe_load(f)["variables_metadata"]

                    LOG.info("Setting variables_metadata %s", name)
                    entry.set_value("/metadata/variables_metadata", variables_metadata)

                finally:
                    shutil.rmtree(dir)


command = Update
