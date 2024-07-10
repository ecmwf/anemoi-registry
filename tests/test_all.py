#!/usr/bin/env python
import os
import subprocess

DATASET = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"
DATASET_PATH = f"{DATASET}.zarr"

pid = os.getpid()

TMP_DATASET = f"{DATASET}-{pid}"
TMP_DATASET_PATH = f"{TMP_DATASET}.zarr"


def run(*args):
    print(" ".join(args))
    try:
        subprocess.check_call(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        e.add_note = f"Command failed: {' '.join(args)}"
        raise


def setup_module():
    run("anemoi-registry", "experiments", "./config.yaml", "--register")
    run("anemoi-registry", "weights", "./test-checkpoint.ckpt", "--register")

    if not os.path.exists(DATASET_PATH):
        run("anemoi-datasets", "create", "dataset_recipe.yaml", DATASET_PATH, "--overwrite")
    assert os.path.exists(DATASET_PATH)

    os.symlink(DATASET_PATH, TMP_DATASET_PATH)
    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--register")
    print("✅ Setup done")


def teardown_module():
    print("✅ Start teardown")
    e = None
    try:
        run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe", "--unregister")
    except Exception as e:
        print(e)

    try:
        run("anemoi-registry", "experiments", "./config.yaml", "--unregister")
    except Exception as e:
        print(e)

    try:
        run("anemoi-registry", "datasets", TMP_DATASET, "--unregister")
        os.remove(TMP_DATASET_PATH)
    except Exception as e:
        print(e)
    if e:
        raise e


def test_datasets():
    # assert run("anemoi-registry", "datasets", TMP_DATASET) == 1
    run("anemoi-registry", "datasets", TMP_DATASET)
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-recipe", "./recipe.yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-status", "testing")
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-location", "/the/dataset/path", "--platform", "atos")
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-location", "/other/path", "--platform", "leonardo")


def test_weights():
    # assert run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe") == 1
    run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe")
    run(
        "anemoi-registry",
        "weights",
        "./test-checkpoint.ckpt",
        "--add-location",
        "s3://ml-weights/a5275e04-0000-0000-a0f6-be19591b09fe.ckpt",
        "--platform",
        "ewc",
    )


def test_experiments():
    # assert run("anemoi-registry", "experiments", "i4df") == 1
    run("anemoi-registry", "experiments", "i4df")
    run("anemoi-registry", "experiments", "i4df", "--add-plots", "./quaver.pdf")
    run("anemoi-registry", "experiments", "i4df", "--add-weights", "./test-checkpoint.ckpt")


def test_list_commands():
    run("anemoi-registry", "list", "experiments")
    run("anemoi-registry", "list", "weights")
    run("anemoi-registry", "list", "datasets")


if __name__ == "__main__":
    test_list_commands()

    setup_module()
    try:
        test_datasets()
        test_weights()
        test_experiments()
    finally:
        teardown_module()
