# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import json
import logging
import os
import shutil
import textwrap
import time

import yaml

from anemoi.registry import Dataset
from anemoi.registry.entry import CatalogueEntryNotFound
from anemoi.registry.entry.dataset import DatasetCatalogueEntryList

LOG = logging.getLogger(__name__)


def _shorten(d):
    return textwrap.shorten(json.dumps(d, ensure_ascii=False, default=str), width=80, placeholder="...")


class Update:

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):

        group = command_parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "-R",
            "--catalogue-from-recipe-file",
            help="Update the catalogue entry from the recipe.",
            action="store_true",
        )

        group.add_argument(
            "-Z",
            "--zarr-file-from-catalogue",
            help="Update the zarr file metadata from a catalogue entry.",
            action="store_true",
        )

        command_parser.add_argument("--dry-run", help="Dry run.", action="store_true")
        command_parser.add_argument("--force", help="Force.", action="store_true")
        command_parser.add_argument("--update", help="Update.", action="store_true")
        command_parser.add_argument("--ignore", help="Ignore some trivial errors.", action="store_true")
        command_parser.add_argument("--resume", help="Resume from progress", action="store_true")
        command_parser.add_argument("--progress", help="Progress file")

        command_parser.add_argument(
            "--continue", help="Continue to the next file on error.", action="store_true", dest="continue_"
        )
        command_parser.add_argument("--workdir", help="Work directory.", default=".")

        command_parser.add_argument("paths", nargs="*", help="Paths to update.")

    def run(self, args):

        if args.resume:
            if args.progress is None:
                LOG.error("Progress file is required for --resume")
                return

            done = set()
            if os.path.exists(args.progress):
                with open(args.progress) as f:
                    for line in f:
                        done.add(line.strip())

        if args.catalogue_from_recipe_file:
            method = self.catalogue_from_recipe_file
        elif args.zarr_file_from_catalogue:
            method = self.zarr_file_from_catalogue

        for path in args.paths:
            if args.resume and path in done:
                LOG.info(f"Skipping {path}")
                continue
            try:
                method(path, args)
            except Exception as e:
                if args.continue_:
                    LOG.exception(e)
                    continue
                raise
            if args.progress:
                with open(args.progress, "a") as f:
                    print(path, file=f)

    def _error(self, args, message):
        LOG.error(message)
        if not args.ignore:
            raise ValueError(message)
        LOG.error("%s", message)
        LOG.warning("Continuing with --ignore.")

    def catalogue_from_recipe_file(self, path, args):
        """Update the catalogue entry a recipe file."""

        from anemoi.datasets import open_dataset
        from anemoi.datasets.create import creator_factory

        def entry_set_value(path, value):
            if args.dry_run:
                LOG.info(f"Would set value {path} to {_shorten(value)}")
            else:
                LOG.info(f"Setting value {path} to {_shorten(value)}")
                entry.set_value(path, value)

        LOG.info(f"Updating catalogue entry from recipe: {path}")

        with open(path) as f:
            recipe = yaml.safe_load(f)

        if "name" not in recipe:
            self._error(args, "Recipe does not contain a 'name' field.")
            return

        name = recipe["name"]
        base, _ = os.path.splitext(os.path.basename(path))

        if name != base:
            self._error(args, f"Recipe name '{name}' does not match file name '{path}'")

        try:
            entry = Dataset(name, params={"_": True})
        except CatalogueEntryNotFound:
            if args.ignore:
                LOG.error(f"Entry not found: {name}")
                return
            raise

        updated = entry.record["metadata"].get("updated", 0)

        if "recipe" in entry.record["_original"]["metadata"]:
            LOG.info("%s: `recipe` already in original. Use --force and --update to update", name)
            if not args.update or not args.force:
                return

        if "recipe" not in entry.record["metadata"] or args.force:
            LOG.info("%s, setting `constant_fields` 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥", name)
            if args.dry_run:
                LOG.info("Would set recipe %s", name)
            else:
                LOG.info("Setting recipe %s", name)
                recipe["name"] = name
                entry_set_value("/metadata/recipe", recipe)
                entry_set_value("/metadata/updated", updated + 1)

        if "constant_fields" in entry.record["metadata"] and "variables_metadata" in entry.record["metadata"]:
            LOG.info("%s, checking `variables_metadata` and `constant_fields`", name)
            constants = entry.record["metadata"]["constant_fields"]
            variables_metadata = entry.record["metadata"]["variables_metadata"]

            changed = False
            for k, v in variables_metadata.items():

                if k in constants and v.get("constant_in_time") is not True:
                    v["constant_in_time"] = True
                    changed = True
                    LOG.info(f"Setting {k} constant_in_time to True")

                if "is_constant_in_time" in v:
                    del v["is_constant_in_time"]
                    changed = True

            if changed:
                if args.debug:
                    with open(f"{name}.variables_metadata.json", "w") as f:
                        print(json.dumps(variables_metadata, indent=2), file=f)
                entry_set_value("/metadata/variables_metadata", variables_metadata)
                entry_set_value("/metadata/updated", updated + 1)
            else:
                LOG.info("No changes required")

        if "variables_metadata" not in entry.record["metadata"] or args.force:
            LOG.info("%s, setting `variables_metadata`  🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥", name)

            if args.dry_run:
                LOG.info("Would set `variables_metadata` %s", name)
            else:

                dir = os.path.join(args.workdir, f"anemoi-registry-commands-update-{time.time()}")
                os.makedirs(dir)

                try:
                    tmp = os.path.join(dir, "tmp.zarr")

                    creator_factory("init", config=path, path=tmp, overwrite=True).run()

                    with open(f"{tmp}/.zattrs") as f:
                        variables_metadata = yaml.safe_load(f)["variables_metadata"]
                    if args.debug:
                        with open(f"{name}.variables_metadata.json", "w") as f:
                            print(json.dumps(variables_metadata, indent=2), file=f)
                    LOG.info("Setting variables_metadata %s", name)
                    entry_set_value("/metadata/variables_metadata", variables_metadata)
                    entry_set_value("/metadata/updated", updated + 1)

                finally:
                    shutil.rmtree(dir)

        if "constant_fields" not in entry.record["metadata"] or args.force:
            LOG.info("%s, setting `constant_fields` 🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥", name)
            ds = open_dataset(name)
            constant_fields = ds.computed_constant_fields()
            LOG.info("%s", constant_fields)
            if args.debug:
                with open(f"{name}.constant_fields.json", "w") as f:
                    print(json.dumps(constant_fields, indent=2), file=f)
            entry_set_value("/metadata/constant_fields", constant_fields)
            entry_set_value("/metadata/updated", updated + 1)

    def zarr_file_from_catalogue(self, path, args):
        import zarr

        LOG.info(f"Updating zarr file from catalogue: {path}")

        z = zarr.open(path)
        metadata = z.attrs.asdict()

        if "uuid" not in metadata:
            self._error(args, "Zarr metadata does not have a 'uuid' field.")

        match = None
        for e in DatasetCatalogueEntryList().get(params={"uuid": metadata["uuid"]}):
            if match:
                self._error(args, f"Multiple entries found for uuid {metadata['uuid']}")
            match = e

        if match is None:
            self._error(args, f"No entry found for uuid {metadata['uuid']}")

        name = match["name"]
        base, _ = os.path.splitext(os.path.basename(path))

        if name != base:
            self._error(args, f"Metadata name '{name}' does not match file name '{path}'")

        try:
            entry = Dataset(name)
        except CatalogueEntryNotFound:
            if args.force:
                LOG.error(f"Entry not found: {name}")
                return
            raise

        def dict_are_different(d1, d2, path=""):

            def _(d):
                return textwrap.shorten(json.dumps(d, ensure_ascii=False), width=80, placeholder="...")

            diff = False

            if d1 == d2:
                return False

            if type(d1) is not type(d2):
                print(f"Type mismatch at {path}: {type(d1)} != {type(d2)}")
                return True

            if isinstance(d1, dict) and isinstance(d2, dict):
                for k in d1.keys():
                    if k not in d2:
                        print(f"Key {path + '.' + k} is missing in the local dictionary {_(d1[k])}")
                        diff = True

                    if k in d1 and k in d2 and dict_are_different(d1[k], d2[k], path + "." + k):
                        diff = True

                for k in d2.keys():
                    if k not in d1:
                        print(f"Key {path + '.' + k} is missing in the remote dictionary {_(d2[k])}")
                        diff = True

                return diff

            if isinstance(d1, list) and isinstance(d2, list):
                if len(d1) != len(d2):
                    print(f"List length mismatch at {path}: {len(d1)} != {len(d2)}")
                    return True

                for i, (a, b) in enumerate(zip(d1, d2)):
                    if dict_are_different(a, b, path + f"[{i}]"):
                        diff = True

                return diff

            if d1 != d2:
                print(f"Value differs at {path}: {d1} != {d2}")
                return True

            return diff

        # Example usage
        entry_metadata = entry.record["metadata"]
        diff = dict_are_different(entry_metadata, metadata)

        if not diff:
            LOG.info(f"Metadata is up to date: {name}")
            return

        if args.dry_run:
            return

        z = zarr.open(path, mode="a")
        LOG.info(f"Updating metadata: {name}")
        z.attrs.update(entry_metadata)


command = Update
