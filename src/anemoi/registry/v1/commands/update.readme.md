# Dataset Metadata Update Tool

This tool provides functionality to synchronize metadata between dataset recipe files, catalogue entries, and Zarr datasets. It ensures consistency across different representations of datasets metadata.

## Prerequisites

- Up-to-date `anemoi-datasets` package in the environment
- Admin access to the catalogue using `anemoi-registry` (need credentials *and* a specific configuration in the anemoi config file).

## Task 1: Update Catalogue from Recipe Files

### Purpose
Updates catalogue entries with the latest metadata derived from recipe files. This involves creating a temporary minimal dataset to extract current metadata values. Note that not all metadata is blindly copied from the minimal datasets, `uuid` and list of dates for instance should not be updated.


### Command
```bash
anemoi-registry update --catalogue-from-recipe-file [--workdir DIR] [options] recipe_files...
```

### Process
1. Creates a temporary minimal dataset using the "init" creator
2. Extracts current metadata including:
   - Recipe information
   - Variables metadata information
   - Additional information when appropriate
3. Updates the catalogue entry with new metadata

### Work Directory
A working directory is required to create the temporary datasets. By default, the working directory is set to the current directory (`.`). You can specify a different directory using the `--workdir` option.

### Options for Catalogue Update
- `--dry-run`: Preview changes without applying them
- `--force`: Update even if entries already exist
- `--update`: Allow updating of existing entries
- `--ignore`: Continue despite trivial errors
- `--workdir DIR`: Specify working directory (default: ".")

### Example
```bash
# Update single recipe
anemoi-registry update --catalogue-from-recipe-file recipe.yaml

# Update multiple recipes, updating existing ones, overwriting metadata if it is already there.
anemoi-registry update --catalogue-from-recipe-file --force --update *.yaml
```

## Task 2: Update Zarr from Catalogue

### Purpose
Synchronizes Zarr metadata with the corresponding metadata from the catalogue, ensuring consistency between stored data and catalogue information.

### Command
```bash
anemoi-registry update --zarr-file-from-catalogue [options] zarr_files...
```

### Process
1. Identifies catalogue entry using Zarr's UUID
2. Compares existing Zarr metadata with catalogue metadata
3. Updates Zarr metadata if differences are found

### Options for Zarr Update
- `--dry-run`: Preview changes without applying them
- `--ignore`: Continue despite non-critical errors
- `--resume`: Resume from previous progress
- `--progress FILE`: Specify progress file for resuming

### Example
```bash
# Update single Zarr
anemoi-registry update --zarr-file-from-catalogue dataset.zarr

# Update multiple Zarr with progress tracking
anemoi-registry update --zarr-file-from-catalogue --progress progress.txt data/*.zarr
```

## Common Options

These options work for both tasks:
- `--dry-run`: Show what would be done without making changes
- `--ignore`: Continue processing despite trivial errors
- `--continue`: Continue to next file on error

## Notes

1. Always use up-to-date version of `anemoi-datasets` package
2. Use `--dry-run` to verify changes before applying them
3. For batch operations, consider using `--progress` to track completion
4. Detailed logging is provided to track the update process
