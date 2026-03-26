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

pytestmark = [pytest.mark.integration, pytest.mark.cli, pytest.mark.s3]

DUMMY_CKPT = os.path.join(os.path.dirname(__file__), "..", "dummy-checkpoint.ckpt")
WEIGHTS_UUID = "a5275e04-0000-0000-a0f6-be19591b09fe"


class TestWeightsAddLocation:
    """Register weights (--no-upload) and add a location with --location-path."""

    @pytest.mark.parametrize("version,cmd", [("1", "weights"), ("2", "weights")])
    def test_register_add_location_unregister(self, run_cli, version, cmd):
        try:
            run_cli(cmd, DUMMY_CKPT, "--register", "--no-upload", version=version)
            run_cli(cmd, WEIGHTS_UUID, version=version)

            run_cli(
                cmd, DUMMY_CKPT,
                "--add-location", "ewc",
                "--location-path", f"s3://ml-weights/{WEIGHTS_UUID}.ckpt",
                version=version,
            )
        finally:
            run_cli(cmd, WEIGHTS_UUID, "--unregister", version=version, check=False)
