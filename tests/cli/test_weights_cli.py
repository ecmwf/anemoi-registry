# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""CLI tests for weights operations — register, add-location with --location-path.

Marked ``s3`` because they register a real checkpoint on the test catalogue.
Run with::

    pytest -m s3 tests/cli/test_weights_cli.py
"""

import os

import pytest

IN_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.cli,
    pytest.mark.s3,
    pytest.mark.skipif(IN_GITHUB, reason="No catalogue token available in GitHub Actions"),
]

DUMMY_CKPT = os.path.join(os.path.dirname(__file__), "..", "dummy-checkpoint.ckpt")
WEIGHTS_UUID = "a5275e04-0000-0000-a0f6-be19591b09fe"


class TestWeightsAddLocation:
    """Register weights (--no-upload) and add a location with --location-path."""

    def test_v1_register_add_location_unregister(self, run_cli):
        try:
            run_cli("weights", DUMMY_CKPT, "--register", "--no-upload", version="1")
            run_cli("weights", WEIGHTS_UUID, version="1")

            run_cli(
                "weights",
                DUMMY_CKPT,
                "--add-location",
                "ewc",
                "--location-path",
                f"s3://ml-weights/{WEIGHTS_UUID}.ckpt",
                version="1",
            )
        finally:
            run_cli("weights", WEIGHTS_UUID, "--unregister", version="1", check=False)

    def test_v2_register_and_unregister(self, run_cli):
        try:
            run_cli("model", "--register", DUMMY_CKPT, "--no-upload", version="2")
            run_cli("model", WEIGHTS_UUID, version="2")
        finally:
            run_cli("model", WEIGHTS_UUID, "--unregister", version="2", check=False)
