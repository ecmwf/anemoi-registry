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

import pytest
import yaml
import zarr
from anemoi.utils.remote import transfer

from anemoi.registry import Dataset

IN_CI = (os.environ.get("GITHUB_WORKFLOW") is not None) or (os.environ.get("IN_CI_HPC") is not None)
ANEMOI_CATALOGUE_TOKEN = os.environ.get("ANEMOI_CATALOGUE_TOKEN")

FORCE_TEST_ENV_VARIABLE = "TEST"
os.environ["ANEMOI_CATALOGUE"] = FORCE_TEST_ENV_VARIABLE

DATASET = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"
DATASET_PATH = f"{DATASET}.zarr"

pid = os.getpid()

TMP_DATASET = f"{DATASET}-{pid}"
TMP_DATASET_PATH = f"{TMP_DATASET}.zarr"
TMP_RECIPE = f"./{TMP_DATASET}.yaml"

REFERENCE_DATASET_URL = "s3://ml-tests/test-data/anemoi-datasets/create/pipe.zarr/"


def run(*args, raise_if_error=True):
    print(" ".join(shlex.quote(arg) for arg in args))
    # input("Press Enter to continue...")
    try:
        env = os.environ.copy()
        env["ANEMOI_CATALOGUE"] = FORCE_TEST_ENV_VARIABLE
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        result.check_returncode()
        return result.stdout
    except Exception as e:
        if raise_if_error:
            print("----------------SDTOUT----------------")
            print(result.stdout)
            print("----------------SDERR----------------")
            print(result.stderr)
            print("-------------------------------------")
        else:
            print("Command failed, but this is expected")
        e.add_note = f"Command failed: {' '.join(args)}"
        raise


def setup_experiments():
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml", "--register")
    run("anemoi-registry", "experiments", "./dummy-recipe-experiment.yaml")


def setup_trainings():
    run("anemoi-registry", "trainings", "./dummy-recipe-training.json", "--register")
    run("anemoi-registry", "trainings", "./dummy-recipe-training.json")


def setup_checkpoints():
    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt", "--register", "--no-upload")
    run("anemoi-registry", "weights", "./dummy-checkpoint.ckpt")


def setup_datasets():
    # cache to avoid downloading the dataset when re-running the tests
    if not os.path.exists(DATASET_PATH):
        transfer(REFERENCE_DATASET_URL, DATASET_PATH, overwrite=True)
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


def setup_module():
    if IN_CI:
        return
    print("# Setup started")
    _teardown_module(raise_if_error=False)
    print()
    setup_experiments()
    setup_trainings()
    setup_checkpoints()
    setup_datasets()
    print("# Setup done")
    print()


def teardown_experiments(errors, raise_if_error):
    try:
        run(
            "anemoi-registry",
            "experiments",
            "./dummy-recipe-experiment.yaml",
            "--unregister",
            raise_if_error=raise_if_error,
        )
    except Exception as e:
        errors.append(e)


def teardown_trainings(errors, raise_if_error):
    # don't tear down because it is created somewhere else
    pass
    # try:
    #     run(
    #         "anemoi-registry",
    #         "trainings",
    #         "./dummy-recipe-training.json",
    #         "--unregister",
    #         raise_if_error=raise_if_error,
    #     )
    # except Exception as e:
    #     errors.append(e)


def teardown_checkpoints(errors, raise_if_error):
    try:
        run(
            "anemoi-registry",
            "weights",
            "a5275e04-0000-0000-a0f6-be19591b09fe",
            "--unregister",
            raise_if_error=raise_if_error,
        )
    except Exception as e:
        errors.append(e)


def teardown_datasets(errors, raise_if_error):
    try:
        os.remove(TMP_RECIPE)
    except Exception as e:
        errors.append(e)

    try:
        shutil.rmtree(TMP_DATASET_PATH)
    except Exception as e:
        errors.append(e)

    try:
        run("anemoi-registry", "datasets", TMP_DATASET, "--unregister", raise_if_error=raise_if_error)
    except Exception as e:
        errors.append(e)


def teardown_module():
    if IN_CI:
        return
    print()
    print("# Teardown")
    _teardown_module(raise_if_error=True)
    print("# Teardown ended")
    print()


def _teardown_module(raise_if_error):
    errors = []
    teardown_experiments(errors, raise_if_error=False)
    teardown_trainings(errors, raise_if_error=False)
    teardown_checkpoints(errors, raise_if_error=False)
    teardown_datasets(errors, raise_if_error=False)
    if errors and raise_if_error:
        for e in errors:
            print(e)
        raise e


@pytest.mark.skipif(IN_CI and not ANEMOI_CATALOGUE_TOKEN, reason="Test requires access to the ANEMOI_CATALOGUE_TOKEN")
def test_settings():
    out = run("anemoi-registry", "settings")
    print(out)


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
def test_datasets():
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

    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--add-location", "ewc")
    # This would actually upload the dataset to the EWC location, but we don't want to do that in tests
    # run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--add-location", "ewc", "--upload")

    # Disable this for now, we need that open_dataset ask the catalogue for the location of the dataset
    # if os.path.exists("/usr/local/bin/mars"):
    #    run("anemoi-registry", "update", "--catalogue-from-recipe-file", TMP_RECIPE, "--force", "--update")
    # run("anemoi-registry", "update", "--zarr-file-from-catalogue", TMP_DATASET_PATH, "--force")


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
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


@pytest.mark.skipif(IN_CI, reason="Test requires access to S3")
def test_experiments():
    run("anemoi-registry", "experiments", "i4df")
    # re-enable when test buckets have been created
    # run("anemoi-registry", "experiments", "i4df", "--add-plots", "./dummy-quaver.pdf")
    # run("anemoi-registry", "experiments", "i4df", "--add-weights", "./dummy-checkpoint.ckpt")


@pytest.mark.skipif(IN_CI and not ANEMOI_CATALOGUE_TOKEN, reason="Test requires access to the ANEMOI_CATALOGUE_TOKEN")
def test_list_commands():
    run("anemoi-registry", "list", "experiments")
    run("anemoi-registry", "list", "weights")
    run("anemoi-registry", "list", "datasets")


if __name__ == "__main__":
    test_list_commands()
    print()

    errors = []
    out = run("anemoi-registry", "settings")
    print(out)

    print("# Start setup")
    setup_datasets()
    try:
        test_datasets()
    finally:
        print("# Start teardown")
        teardown_datasets(errors, raise_if_error=False)

    print()

    print("# Start setup")
    setup_experiments()
    try:
        test_experiments()
    finally:
        print("# Start teardown")
        teardown_experiments(errors, raise_if_error=False)

    print()

    print("# Start setup")
    setup_trainings()
    print("# Start teardown")
    teardown_trainings(errors, raise_if_error=False)

    print()

    print("# Start setup")
    setup_checkpoints()
    try:
        test_weights()
    finally:
        print("# Start teardown")
        teardown_checkpoints(errors, raise_if_error=False)

    if errors:
        for e in errors:
            print(e)
        raise e
