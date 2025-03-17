# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import os
import shlex
import shutil
import subprocess
import uuid

import yaml
import zarr
from anemoi.utils.remote import transfer

from anemoi.registry import Dataset

DATASET = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"
DATASET_PATH = f"{DATASET}.zarr"

pid = os.getpid()

TMP_DATASET = f"{DATASET}-{pid}"
TMP_DATASET_PATH = f"{TMP_DATASET}.zarr"
TMP_RECIPE = f"./{TMP_DATASET}.yaml"

DATASET_URL = "s3://ml-tests/test-data/anemoi-datasets/create/pipe.zarr/"


def run(*args):
    print(" ".join(shlex.quote(arg) for arg in args))
    # input("Press Enter to continue...")
    try:
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        result.check_returncode()
    except Exception as e:
        print("----------------SDTOUT----------------")
        print(result.stdout)
        print("----------------SDERR----------------")
        print(result.stderr)
        print("-------------------------------------")
        e.add_note = f"Command failed: {' '.join(args)}"
        raise


def setup_experiments():
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml", "--register")
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml")


def setup_checkpoints():
    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt", "--register")
    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt")


def setup_datasets():
    # cache to avoid downloading the dataset when re-running the tests
    if not os.path.exists(DATASET_PATH):
        transfer(DATASET_URL, DATASET_PATH, overwrite=True)
    assert os.path.exists(DATASET_PATH)

    # create a temporary recipe file with the right name in
    with open("./recipe.yaml", "r") as f:
        r = yaml.load(f, Loader=yaml.FullLoader)
    r["name"] = TMP_DATASET
    with open(TMP_RECIPE, "w") as f:
        yaml.dump(r, f)

    # set new uuid to the tmp dataset
    shutil.copytree(DATASET_PATH, TMP_DATASET_PATH)
    z = zarr.open(TMP_DATASET_PATH)
    z.attrs["uuid"] = str(uuid.uuid4())

    # register the dataset
    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--register")

    # check that the dataset is registered
    run("anemoi-registry", "datasets", TMP_DATASET_PATH)

    print("# Setup done")


def _setup_module():
    _teardown_module(raise_if_error=False)
    setup_experiments()
    setup_checkpoints()
    setup_datasets()


def teardown_experiments(errors):
    try:
        run("anemoi-registry", "experiments", "./dummp-recipe-experiment.yaml", "--unregister")
    except Exception as e:
        errors.append(e)


def teardown_checkpoints(errors):
    try:
        run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe", "--unregister")
    except Exception as e:
        errors.append(e)


def teardown_datasets(errors):
    try:
        run("anemoi-registry", "datasets", TMP_DATASET, "--unregister")
    except Exception as e:
        errors.append(e)

    try:
        os.remove(TMP_RECIPE)
    except Exception as e:
        errors.append(e)

    try:
        shutil.rmtree(TMP_DATASET_PATH)
    except Exception as e:
        errors.append(e)


def _teardown_module(raise_if_error=True):
    errors = []
    teardown_experiments(errors)
    teardown_checkpoints(errors)
    teardown_datasets(errors)
    if errors and raise_if_error:
        for e in errors:
            print(e)
        raise e


def _test_datasets():
    # assert run("anemoi-registry", "datasets", TMP_DATASET) == 1
    run("anemoi-registry", "datasets", TMP_DATASET)
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-recipe", TMP_RECIPE)
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

    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST={}", "yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.a={}", "yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.a.string=ok")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.a.int=42", "int")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.a.float=42", "float")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.a.datetime=2015-04-18", "datetime")
    # run("echo", "45", "|", "anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.b=-", "stdin")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.c={a: 43}", "yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-metadata", "TEST.d=test.json", "path")
    actual = Dataset(TMP_DATASET).record["metadata"]["TEST"]
    expected = {
        "a": {"string": "ok", "int": 42, "float": 42.0, "datetime": "2015-04-18T00:00:00"},
        "c": {"a": 43},
        "d": {"a": 45},
    }
    assert actual == expected, (actual, expected)

    run("anemoi-registry", "datasets", TMP_DATASET, "--remove-metadata", "TEST")
    metadata = Dataset(TMP_DATASET).record["metadata"]
    assert "TEST" not in metadata, metadata["TEST"]

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

    # This is poluting the s3 bucket, we should have a way to clean it up automatically
    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--add-location", "ewc", "--upload")

    if os.path.exists("/usr/local/bin/mars"):
        run("anemoi-registry", "update", "--catalogue-from-recipe-file", TMP_RECIPE, "--force", "--update")
    run("anemoi-registry", "update", "--zarr-file-from-catalogue", TMP_DATASET_PATH, "--force")


def _test_weights():
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


def _test_experiments():
    run("anemoi-registry", "experiments", "i4df")
    run("anemoi-registry", "experiments", "i4df", "--add-plots", "./dummy-quaver.pdf")
    run("anemoi-registry", "experiments", "i4df", "--add-weights", "./dummy-checkpoint.ckpt")


def _test_list_commands():
    run("anemoi-registry", "list", "experiments")
    run("anemoi-registry", "list", "weights")
    run("anemoi-registry", "list", "datasets")


def test_print():
    print("test")


if __name__ == "__main__":
    _test_list_commands()
    print()

    errors = []

    print("# Start setup")
    setup_datasets()
    try:
        _test_datasets()
    finally:
        print("# Start teardown")
        teardown_datasets(errors)

    print()

    print("# Start setup")
    setup_experiments()
    try:
        _test_experiments()
    finally:
        print("# Start teardown")
        teardown_experiments(errors)

    print()

    print("# Start setup")
    setup_checkpoints()
    try:
        _test_weights()
    finally:
        print("# Start teardown")
        teardown_checkpoints(errors)

    if errors:
        for e in errors:
            print(e)
        raise e
