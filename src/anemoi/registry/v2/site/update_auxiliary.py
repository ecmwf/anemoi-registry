# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Download auxiliary files specified in site config."""

import logging
import os
from pathlib import Path

from .config import load_task_config

LOG = logging.getLogger(__name__)


def update_auxiliary(is_test=False):
    """Download auxiliary files specified in auxiliary.json."""
    from anemoi.utils.remote import transfer

    auxiliary = load_task_config("update-auxiliary")

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

        if is_test:
            print("  Dry run: skipping transfer")
            continue

        target_dir.mkdir(parents=True, exist_ok=True)
        transfer(source, str(target), resume=True)
        print("  Done")
