# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


"""Command place holder. Delete when we have real commands."""

import csv
import io
import json
import logging
import os
import sys

import yaml
from anemoi.utils.humanize import json_pretty_dump
from requests.exceptions import HTTPError

from ..entry import VALUES_PARSERS
from ..entry import CatalogueEntryNotFound
from ..rest import RestItemList
from ..utils import list_to_dict
from . import Command

LOG = logging.getLogger(__name__)

LIST_FORMATS = ["text", "csv", "json", "rich"]


def _handle_field_error(exc):
    """Print a user-friendly message when the server rejects unknown fields."""
    resp = getattr(exc, "response", None)
    if resp is not None and resp.status_code == 400:
        try:
            body = resp.json()
        except Exception:
            return
        if "available_fields" in body:
            print(f"Error: {body['error']}", file=sys.stderr)
            print("Available fields:", ", ".join(body["available_fields"]), file=sys.stderr)
            sys.exit(1)


def _collect_keys(rows, prefix=""):
    """Collect all available dotted-path keys from a list of dicts."""
    keys = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for k, v in row.items():
            full = f"{prefix}{k}"
            keys.add(full)
            if isinstance(v, dict):
                keys.update(_collect_keys([v], prefix=f"{full}."))
    return keys


def _validate_fields(rows, fields):
    """Raise ValueError if any requested field is not present in the data."""
    if not rows:
        return
    available = _collect_keys(rows)
    bad = [f for f in fields if f not in available]
    if bad:
        suggestion = ", ".join(sorted(available))
        bad_str = ", ".join(bad)
        raise ValueError(f"Unknown field(s): {bad_str}. " f"Available fields: {suggestion}")


def format_list_output(rows, fields, fmt="text") -> None:
    """Format a list of dicts for output.

    Parameters
    ----------
    rows : list[dict]
        The data to format.
    fields : list[str]
        Column names to include.  Supports dotted paths (e.g. ``metadata.shape``).
    fmt : str
        One of ``text``, ``csv``, ``json``, ``rich``.
    """

    def _get(row, field):
        """Resolve a possibly-dotted field from a dict."""
        value = row
        for part in field.split("."):
            if isinstance(value, dict):
                value = value.get(part, "")
            else:
                return ""
        return value if value is not None else ""

    if fmt == "json":
        if fields:
            rows = [{f: _get(r, f) for f in fields} for r in rows]
        print(json_pretty_dump(rows))
        return

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(fields)
        for r in rows:
            writer.writerow([_get(r, f) for f in fields])
        sys.stdout.write(buf.getvalue())
        return

    if fmt == "rich":
        from rich.console import Console
        from rich.table import Table

        table = Table(show_lines=False)
        for f in fields:
            table.add_column(f)
        for r in rows:
            table.add_row(*[str(_get(r, f)) for f in fields])
        Console().print(table)
        return

    # default: text  (tab-separated)
    for r in rows:
        print("\t".join(str(_get(r, f)) for f in fields))


class BaseCommand(Command):
    internal = True
    timestamp = True

    def is_path(self, name_or_path):
        return os.path.exists(name_or_path)

    def is_identifier(self, name_or_path):
        try:
            self.entry_class(key=name_or_path)
            return True
        except CatalogueEntryNotFound:
            return False

    def process_task(self, entry, args, k, func_name=None, /, _skip_if_not_found=False, **kwargs):
        """Call the method `k` on the entry object.
        The args/kwargs given to the method are extracted from from the argument `k` in the `args` object.

        Additionally the argument `k` is casted to the correct type,
        depending on if this is a string, int, float, list or dict, or a boolean.

        The provided **kwargs are also passed to the method.
        The method name can be changed by providing the `func_name` argument.
        """
        if entry is None and _skip_if_not_found:
            LOG.warning(f"Cannot find entry {args.NAME_OR_PATH}. Skipping {k}.")
            return

        assert isinstance(k, str), k
        if func_name is None:
            func_name = k

        v = getattr(args, k)

        if v is None:
            return
        if v is True:
            LOG.debug(f"{entry.key} : Processing task {k}")
            return getattr(entry, func_name)(**kwargs)
        if v is False:
            return
        if isinstance(v, (str, int, float)):
            LOG.debug(f"{entry.key} : Processing task {k} with {v}")
            return getattr(entry, func_name)(v, **kwargs)
        if isinstance(v, list):
            v_str = ", ".join(str(x) for x in v)
            LOG.debug(f"{entry.key} : Processing task {k} with {v_str}")
            return getattr(entry, func_name)(*v, **kwargs)
        if isinstance(v, dict):
            v_str = ", ".join(f"{k_}={v_}" for k_, v_ in v.items())
            LOG.debug(f"{entry.key} : Processing task {k} with {v_str}")
            return getattr(entry, func_name)(**v, **kwargs)
        raise ValueError(f"Invalid task {k}={v}. type(v)= {type(v)}")

    def run(self, args):
        LOG.debug(f"anemoi-registry args: {args}")
        if hasattr(args, "list") and args.list is not None:
            return self.run_list(args)
        entry = self.get_entry(args)
        self._run(entry, args)

    #: Default fields shown by ``--list`` when ``--list-fields`` is not given.
    #: Subclasses should override this.
    list_default_fields = None

    def run_list(self, args):
        """List entries in the catalogue, with optional key=value filters."""
        request = list_to_dict(args.list) if args.list else {}
        fmt = getattr(args, "list_format", "text")
        fields = getattr(args, "list_fields", None)
        sort = getattr(args, "list_sort", None)
        if not fields:
            fields = self.list_default_fields or [self.entry_class.main_key]

        params = dict(request)
        # Pass requested fields to the server for validation + projection
        params["fields"] = ",".join(fields)
        if sort:
            params["sort"] = sort

        try:
            payload = RestItemList(self.entry_class.collection).get(params=params)
        except HTTPError as e:
            _handle_field_error(e)
            raise
        format_list_output(payload, fields, fmt)

    def add_list_arguments(self, command_parser):
        """Add ``--list``, ``--list-fields`` and ``--list-format`` to the parser."""
        command_parser.add_argument(
            "--list",
            help=f"List {self.kind}s in the catalogue. Optional key=value filters.",
            nargs="*",
            metavar="K=V",
        )
        command_parser.add_argument(
            "--list-fields",
            help="Comma-separated field names to display (supports dotted paths, e.g. metadata.shape).",
            type=lambda s: [f.strip() for f in s.split(",")],
            metavar="FIELDS",
        )
        command_parser.add_argument(
            "--list-sort",
            help="Comma-separated fields to sort by.",
            metavar="FIELDS",
        )
        command_parser.add_argument(
            "--list-format",
            help="Output format for --list.",
            choices=LIST_FORMATS,
            default="rich",
        )

    def get_entry(self, args, must_exist=False):
        return self.entry_class.load_from_anything(
            key=args.NAME_OR_PATH,
            path=args.NAME_OR_PATH if self.is_path(args.NAME_OR_PATH) else None,
            must_exist=must_exist,
            kwargs=vars(args),
        )

    def run_from_identifier(self, *args, **kwargs):
        raise NotImplementedError()

    def run_from_path(self, *args, **kwargs):
        raise NotImplementedError()

    def set_get_remove_metadata(self, entry, args):

        if args.get_metadata:
            value = entry.get_value(args.get_metadata[0])
            if len(args.get_metadata) > 1:
                type_ = args.get_metadata[1]
                value = dict(str=str, yaml=yaml.safe_dump, json=json.dumps)[type_](value)
            print(value)

        if args.set_metadata:
            path, value = args.set_metadata[0].split("=", 1)
            type_ = args.set_metadata[1] if len(args.set_metadata) > 1 else None
            entry.set_value(path, value, type_=type_, increment_update=True)

        if args.remove_metadata:
            entry.remove_value(args.remove_metadata, increment_update=True)

    def add_set_get_remove_metadata_arguments(self, command_parser):
        command_parser.add_argument(
            "--get-metadata",
            help=(
                f"Get a metadata value from the {self.kind} catalogue record (KEY, [TYPE]). "
                "KEY is a '.' separated path to the value. "
                "TYPE is the output format : str (default), yaml, json."
            ),
            nargs="+",
            metavar=("KEY", "TYPE"),
        )
        command_parser.add_argument(
            "--set-metadata",
            help=(
                f"Set a metadata value to the {self.kind} catalogue record (KEY=VALUE, [TYPE]). "
                "KEY is a '.' separated path to the value. "
                f"TYPE is the input type : {', '.join(VALUES_PARSERS.keys())}. "
                "Default type is 'str'. "
                "TYPE 'int', 'float', 'bool', 'datetime', 'timedelta' cast the VALUE before storing it. "
                "TYPE 'json' and 'yaml' parse the VALUE before storing it. "
                "TYPE 'path' reads the file provided as VALUE (.json, .yaml, etc). "
                "TYPE 'stdin' reads the value from the standard input, ignoring the VALUE. "
            ),
            nargs="+",
            metavar=("KEY=VALUE", "TYPE"),
        )
        command_parser.add_argument(
            "--remove-metadata",
            help=f"Delete a metadata value to the {self.kind} catalogue record (KEY)",
            metavar="KEY",
        )
