.. _howto-models:

###################
 Models (weights)
###################

This guide covers how to upload, download, and manage trained model
checkpoints (also called *weights*) in the Anemoi catalogue.

.. note::

   In **v2**, the command is called ``model``. In **v1**, it is called
   ``weights``. The underlying catalogue collection is the same.
   **v2 is recommended** for new workflows.
   See :ref:`cli-versions` for how to switch.

   .. code-block:: bash

      # Enable v2 (recommended)
      export ANEMOI_REGISTRY_CLI_VERSION=2


*****************************
 Uploading a model
*****************************

Write and S3 credentials are required. See :ref:`configuring`.

v2 (recommended)
=================

Register and upload a model checkpoint in a single step:

.. code-block:: bash

   anemoi-registry model --register /path/to/my-model.ckpt

   # Specify the type of weights (default: training)
   anemoi-registry model --register /path/to/my-model.ckpt --type inference

   # Overwrite if already registered (use with caution)
   anemoi-registry model --register /path/to/my-model.ckpt --overwrite


v1 (legacy)
============

In previous versions (v1), the command was ``weights`` and the syntax was different.

.. code-block:: bash

   # Register and upload
   anemoi-registry weights /path/to/my-model.ckpt --register

   # Register without uploading
   anemoi-registry weights /path/to/my-model.ckpt --register --no-upload

   # Add a location on a specific platform
   anemoi-registry weights my-model --add-location ewc


*****************************
 Downloading a model
*****************************

.. code-block:: bash

   # v2
   anemoi-registry model my-model --download /path/to/save/my-model.ckpt

S3 read credentials are required. See :ref:`configuring`.


*****************************
 Listing models
*****************************

.. code-block:: bash

   # v2
   anemoi-registry model --list

****************************************
 Messing with metadata (not recommended)
****************************************

.. code-block:: bash

   # v2
   anemoi-registry model my-model --metadata get description
   anemoi-registry model my-model --metadata set description="My fine-tuned model"
   anemoi-registry model my-model --metadata delete some_key
