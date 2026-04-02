.. _howto-experiments:

#############
 Experiments
#############

This guide covers how to register and manage experiments in the Anemoi
catalogue.

.. admonition:: ECMWF internal

   The ``experiment`` command is primarily used by ECMWF internal
   workflows for tracking operational and research experiments. It is
   tightly coupled to the ECMWF experiment infrastructure. External
   users will typically not need this command. It may be removed or
   replaced in a future release.


*****************************
 Overview
*****************************

An *experiment* in the catalogue tracks a model development cycle —
including its configuration, training weights, evaluation plots, and
archive metadata. Experiments can have multiple *run numbers*, each
containing its own set of weights, plots, and archive files.


*****************************
 CLI versions
*****************************

The ``experiment`` command exists in both v1 and v2. v2 is recommended.
See :ref:`cli-versions` for how to switch.

.. code-block:: bash

   # Enable v2 (recommended)
   export ANEMOI_REGISTRY_CLI_VERSION=2

Key differences:

- In **v1**, the positional argument is ``NAME_OR_PATH`` (can be a name
  or a path to a YAML config file).
- In **v2**, the positional argument is ``NAME`` only. Paths are
  provided via action flags.
- In **v2**, metadata flags use ``--metadata get/set/delete`` instead of
  ``--get-metadata/--set-metadata/--remove-metadata``.


*****************************
 Registering an experiment
*****************************

.. code-block:: bash

   # v2
   anemoi-registry experiment my-experiment --register

   # v1
   anemoi-registry experiments my-experiment --register

   # Overwrite if already exists
   anemoi-registry experiment my-experiment --register --overwrite


*****************************
 Adding weights and plots
*****************************

.. code-block:: bash

   # Add weight files (uploads to S3 automatically)
   anemoi-registry experiment my-experiment --add-weights model-epoch10.ckpt model-epoch20.ckpt

   # Add plot files
   anemoi-registry experiment my-experiment --add-plots loss-curve.png metrics.png


*****************************
 Setting metadata
*****************************

.. code-block:: bash

   # Set a simple key-value pair (scoped to a run number if given)
   anemoi-registry experiment my-experiment --set-key description "First run"
   anemoi-registry experiment my-experiment --set-key description "Run 3" --run-number 3

   # Set a key from a JSON/YAML file
   anemoi-registry experiment my-experiment --set-key-json config config.yaml

   # v2 generic metadata
   anemoi-registry experiment my-experiment --metadata get status
   anemoi-registry experiment my-experiment --metadata set status=active


*****************************
 Archive management
*****************************

Experiments can have archive metadata files associated with run numbers
and platforms:

.. code-block:: bash

   # Register archive metadata
   anemoi-registry experiment my-experiment --set-archive archive.json \
       --run-number 1 --archive-platform atos

   # Retrieve archive metadata
   anemoi-registry experiment my-experiment --get-archive output.json \
       --run-number 1 --archive-platform atos

   # Retrieve merged archive for all runs
   anemoi-registry experiment my-experiment --get-archive merged.json \
       --run-number all

   # Remove archive metadata
   anemoi-registry experiment my-experiment --remove-archive \
       --run-number 1 --archive-platform atos

   # Record that an archive moved between platforms
   anemoi-registry experiment my-experiment --archive-moved atos lumi \
       --run-number 1


*****************************
 Other operations
*****************************

.. code-block:: bash

   # List experiments
   anemoi-registry experiment --list

   # View in browser
   anemoi-registry experiment my-experiment --view

   # Print catalogue URL
   anemoi-registry experiment my-experiment --url

   # Delete artefacts (plots, etc.)
   anemoi-registry experiment my-experiment --delete-artefacts

   # Unregister
   anemoi-registry experiment my-experiment --unregister


*****************************
 Migrating from v1 to v2
*****************************

.. list-table::
   :widths: 50 50
   :header-rows: 1

   -  -  v1
      -  v2

   -  -  ``anemoi-registry experiments NAME_OR_PATH``
      -  ``anemoi-registry experiment NAME``

   -  -  ``--get-metadata KEY``
      -  ``--metadata get KEY``

   -  -  ``--set-metadata KEY VALUE``
      -  ``--metadata set KEY=VALUE``

   -  -  ``--remove-metadata KEY``
      -  ``--metadata delete KEY``
