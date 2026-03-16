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

from anemoi.utils.humanize import json_pretty_dump

from . import Command

LOG = logging.getLogger(__name__)


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} EB"


def _pct(used, total) -> str:
    if not total:
        return "n/a"
    return f"{100 * used / total:.1f}%"


def _format_resource(item: dict) -> str:
    lines = [
        f"  Site      : {item.get('site', 'n/a')}",
        f"  Path      : {item.get('path', 'n/a')}",
        f"  Storage   : {_human_bytes(item['bytes'])} / {_human_bytes(item['bytes_quota'])} ({_pct(item['bytes'], item['bytes_quota'])})",
        f"  Objects   : {item['objects']:,} / {item['objects_quota']:,} ({_pct(item['objects'], item['objects_quota'])})",
        f"  Timestamp : {item.get('timestamp', 'n/a')}",
    ]
    return "\n".join(lines)


def _parse_filters(filters: list[str]) -> dict:
    params = {}
    for f in filters:
        key, _, value = f.partition("=")
        params[key.strip()] = value.strip()
    return params


def _load_json_or_file(value: str) -> dict:
    import os

    if os.path.exists(value):
        with open(value) as fh:
            return json.load(fh)
    return json.loads(value)


class Resources(Command):
    """List or post resources in the catalogue."""

    internal = True
    timestamp = True

    def add_arguments(self, command_parser):
        command_parser.add_argument(
            "--filter",
            nargs="+",
            metavar="KEY=VALUE",
            help="Filter results by KEY=VALUE pairs.",
        )
        command_parser.add_argument(
            "--post",
            metavar="FILE_OR_JSON",
            help="Post a new resource from a JSON file path or an inline JSON string.",
        )

    def run(self, args):
        from ..entry.resource import ResourceCatalogueEntryList

        lst = ResourceCatalogueEntryList()

        if args.post:
            data = _load_json_or_file(args.post)
            result = lst.post(data)
            print(json_pretty_dump(result))
            return

        params = _parse_filters(args.filter) if args.filter else {}
        result = lst.get(params=params)
        if isinstance(result, dict):
            result = [result]
        for item in result:
            print(_format_resource(item))


command = Resources
