# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import subprocess

from anemoi.utils.remote import transfer

DATASET = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"
DATASET_PATH = f"{DATASET}.zarr"

pid = os.getpid()

TMP_DATASET = f"{DATASET}-{pid}"
TMP_DATASET_PATH = f"{TMP_DATASET}.zarr"

DATASET_URL = "s3://ml-tests/test-data/anemoi-datasets/create/pipe.zarr/"


def run(*args):
    print(" ".join(args))
    try:
        subprocess.check_call(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        e.add_note = f"Command failed: {' '.join(args)}"
        raise


def setup_module():
    teardown_module(raise_if_error=False)
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml", "--register")
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml")

    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt", "--register")
    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt")

    if not os.path.exists(DATASET_PATH):
        transfer(DATASET_URL, DATASET_PATH, overwrite=True)
        import uuid

        import zarr

        z = zarr.open(DATASET_PATH)
        z.attrs["uuid"] = str(uuid.uuid4())
    assert os.path.exists(DATASET_PATH)

    os.symlink(DATASET_PATH, TMP_DATASET_PATH)
    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--register")
    run("anemoi-registry", "datasets", TMP_DATASET_PATH)
    print("# Setup done")


def teardown_module(raise_if_error=True):
    error = None
    try:
        run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe", "--unregister")
    except Exception as e:
        error = e

    try:
        run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml", "--unregister")
    except Exception as e:
        error = e

    try:
        run("anemoi-registry", "datasets", TMP_DATASET, "--unregister")
        os.remove(TMP_DATASET_PATH)
    except Exception as e:
        error = e
    if error and raise_if_error:
        raise error


def test_datasets():
    # assert run("anemoi-registry", "datasets", TMP_DATASET) == 1
    run("anemoi-registry", "datasets", TMP_DATASET)
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-recipe", "./dummy-recipe-dataset.yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-status", "testing")
    run(
        "anemoi-registry",
        "datasets",
        TMP_DATASET,
        "--add-location",
        "atos",
        "--uri-pattern",
        "/the/dataset/path/{name}",
    )
    run(
        "anemoi-registry",
        "datasets",
        TMP_DATASET,
        "--add-location",
        "leonardo",
        "--uri-pattern",
        "https://other/{name}/path",
    )
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-location", "ewc")

    # do not upload the dataset to avoid polluting the s3 bucket, until we have a way to clean it up automatically
    # run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--add-location", "ewc", "--upload")


def test_weights():
    # assert run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe") == 1
    run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe")
    run(
        "anemoi-registry",
        "weights",
        "./dummy-checkpoint.ckpt",
        "--add-location",
        "ewc",
        "--location-path",
        "s3://ml-weights/a5275e04-0000-0000-a0f6-be19591b09fe.ckpt",
    )


def test_experiments():
    run("anemoi-registry", "experiments", "i4df")
    run("anemoi-registry", "experiments", "i4df", "--add-plots", "./dummy-quaver.pdf")
    run("anemoi-registry", "experiments", "i4df", "--add-weights", "./dummy-checkpoint.ckpt")


def test_list_commands():
    run("anemoi-registry", "list", "experiments")
    run("anemoi-registry", "list", "weights")
    run("anemoi-registry", "list", "datasets")


if __name__ == "__main__":
    test_list_commands()
    print()

    print("# Start setup")
    setup_module()
    try:
        print()
        test_datasets()
        print()
        test_weights()
        print()
        test_experiments()
        print()
    finally:
        print("# Start teardown")
        teardown_module()
