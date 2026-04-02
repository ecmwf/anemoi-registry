.. _howto-training:

##########
 Training
##########

This guide covers how to register and manage training runs in the
Anemoi catalogue.

.. admonition:: ECMWF internal

   The ``training`` command is primarily used by ECMWF internal
   workflows for tracking training runs. It is tightly coupled to the
   ECMWF training infrastructure. External users will typically not
   need this command. It may be removed or replaced in a future
   release.


*****************************
 Overview
*****************************

A *training* entry in the catalogue tracks a specific model training
run — including its configuration, resulting weights, and metadata.
Trainings are distinct from experiments: an experiment may span multiple
training runs and evaluation cycles.


*****************************
 CLI versions
*****************************

The ``training`` command exists in both v1 (as ``trainings``) and v2
(as ``training``). v2 is recommended. See :ref:`cli-versions`.

.. code-block:: bash

   # Enable v2 (recommended)
   export ANEMOI_REGISTRY_CLI_VERSION=2

Key differences:

- In **v1**, the positional argument is ``NAME_OR_PATH`` (a name or a
  path to a JSON config file). The command is ``trainings`` (plural).
- In **v2**, the positional argument is ``NAME`` only. The command is
  ``training`` (singular).
- In **v2**, metadata flags use ``--metadata get/set/delete``.


*****************************
 Registering a training run
*****************************

.. code-block:: bash

   # v2
   anemoi-registry training my-training --register

   # v1
   anemoi-registry trainings my-training.json --register

   # Overwrite if already exists
   anemoi-registry training my-training --register --overwrite


*****************************
 Working with metadata
*****************************

.. code-block:: bash

   # v2
   anemoi-registry training my-training --metadata get status
   anemoi-registry training my-training --metadata set status=completed
   anemoi-registry training my-training --metadata delete some_key

   # v1
   anemoi-registry trainings my-training --set-key status completed
   anemoi-registry trainings my-training --set-key-json config config.json


*****************************
 Listing and unregistering
*****************************

.. code-block:: bash

   # List
   anemoi-registry training --list

   # Unregister
   anemoi-registry training my-training --unregister


*****************************
 Migrating from v1 to v2
*****************************

.. list-table::
   :widths: 50 50
   :header-rows: 1

   -  -  v1
      -  v2

   -  -  ``anemoi-registry trainings NAME_OR_PATH``
      -  ``anemoi-registry training NAME``

   -  -  ``--set-key KEY VALUE``
      -  ``--metadata set KEY=VALUE``

   -  -  ``--set-key-json KEY FILE``
      -  ``--metadata set KEY=VALUE json``

   -  -  ``--get-metadata KEY``
      -  ``--metadata get KEY``

   -  -  ``--set-metadata KEY VALUE``
      -  ``--metadata set KEY=VALUE``

   -  -  ``--remove-metadata KEY``
      -  ``--metadata delete KEY``
