import os
import subprocess

TEST_DATASET_INPUT = "aifs-ea-an-oper-0001-mars-20p0-1979-1979-6h-v0-testing"

pid = os.getpid()
TMP_DATASET = f"{TEST_DATASET_INPUT}-{pid}"

TMP_DATASET_PATH = f"./data/{TMP_DATASET}.zarr"


def run(*args):
    print(" ".join(args))
    try:
        subprocess.check_call(args)
    except Exception as e:
        e.add_note = f"Command failed: {' '.join(args)}"

        raise


def setup_module():
    run("anemoi-datasets", "create", "dataset_recipe.yaml", TMP_DATASET_PATH, "--overwrite")
    assert os.path.exists(TMP_DATASET_PATH)


# def teardown_module():
#    run("anemoi-registry", "datasets", TMP_DATASET, "--unregister")
#    os.remove(TMP_DATASET_PATH)


def test_datasets():
    run("anemoi-registry", "datasets", TMP_DATASET_PATH, "--register")
    # assert run("anemoi-registry", "datasets", TMP_DATASET) == 1
    run("anemoi-registry", "datasets", TMP_DATASET)
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-recipe", "./data/recipe.yaml")
    run("anemoi-registry", "datasets", TMP_DATASET, "--set-status", "testing")
    run("anemoi-registry", "datasets", TMP_DATASET, "--add-location", "/the/dataset/path", "--platform", "atos")
    run(
        "anemoi-registry",
        "datasets",
        TMP_DATASET,
        "--add-location",
        "/the/dataset/path/other",
        "--platform",
        "leonardo",
    )


def test_weights():
    run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe", "--unregister")
    # assert run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe") == 1
    run("anemoi-registry", "weights", "./data/test-checkpoint.ckpt", "--register")
    run("anemoi-registry", "weights", "a5275e04-0000-0000-a0f6-be19591b09fe")
    run(
        "anemoi-registry",
        "weights",
        "./data/test-checkpoint.ckpt",
        "--add-location",
        "s3://ml-weights/a5275e04-0000-0000-a0f6-be19591b09fe.ckpt",
        "--platform",
        "ewc",
    )


def test_experiments():
    run("anemoi-registry", "experiments", "./data/config.yaml", "--unregister")
    # assert run("anemoi-registry", "experiments", "i4df") == 1
    run("anemoi-registry", "experiments", "./data/config.yaml", "--register")
    run("anemoi-registry", "experiments", "i4df")
    run("anemoi-registry", "experiments", "i4df", "--add-plots", "./data/quaver.pdf")
    run("anemoi-registry", "experiments", "i4df", "--add-weights", "./data/test-checkpoint.ckpt")


def test_list_commands():
    run("anemoi-registry", "list", "experiments", ">", "e.txt")
    run("anemoi-registry", "list", "weights", ">", "w.txt")
    run("anemoi-registry", "list", "datasets", ">", "d.txt")
