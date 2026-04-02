.. _howto-datasets:

##########
 Datasets
##########

This guide covers how to register, manage, and troubleshoot datasets in
the Anemoi catalogue.

.. note::

   The command is called ``dataset`` in v2 and ``datasets`` in v1.
   **v2 is recommended** for new workflows. See :ref:`cli-versions`
   for how to switch. Throughout this guide, v2 commands are shown
   first, with v1 equivalents noted where they differ.

   .. code-block:: bash

      # Enable v2 (recommended)
      export ANEMOI_REGISTRY_CLI_VERSION=2


*****************************
 Datasets vs replicas
*****************************

A **dataset** is a unique entry in the catalogue. It has a name,
metadata (recipe, status, variables, etc.), and is created once.

A **replica** is a physical copy of a dataset stored at a specific site.
A single dataset can have multiple replicas across different sites (e.g.
one on S3, one on a local Lustre filesystem). Replicas track where the
data physically lives.

In **v1**, replicas were managed as "locations" within the ``datasets``
command (``--add-location``, ``--remove-location``). In **v2**, replica
management uses a dedicated ``replica`` command for clarity.

Dataset names must follow the :ref:`naming conventions <naming-conventions>`.


*****************************
 Registering a dataset
*****************************

After creating a dataset locally (using ``anemoi-datasets``), register
it in the catalogue so that other users can discover it.

Write credentials are required. See :ref:`configuring`.

.. code-block:: bash

   # Register — NAME is deduced from the path basename
   anemoi-registry dataset --register /path/to/my-dataset.zarr

   # Set metadata
   anemoi-registry dataset DATASET --set-status experimental --set-recipe ./recipe.yaml


Previously, in v1, registration was done with the ``datasets`` command, with a different syntax.

*****************************
 Uploading a dataset to S3
*****************************

Once the dataset is registered in the catalogue, the data has not been moved.
You can upload the data to a remote site and register the replica.

Uploading and managing replicas is done through the ``replica`` command:

.. code-block:: bash

   # Upload to a site (e.g. ewc) — registers the replica automatically
   anemoi-registry replica ewc my-dataset --upload /path/to/my-dataset.zarr

   # Use more threads MAY allow faster transfers (default: 2)
   anemoi-registry replica ewc my-dataset --upload /path/to/my-dataset.zarr --threads 8


S3 credentials are required. See :ref:`configuring`.

Previously, in v1, replicas were managed as "locations" within the ``datasets``.


*****************************
 Listing datasets
*****************************

.. code-block:: bash

   # v2 only:
   anemoi-registry dataset --list


*****************************
 Listing replicas
*****************************


.. code-block:: bash

   # v2 only:
   anemoi-registry replica --list
   anemoi-registry replica --list site=ewc
   anemoi-registry replica --list name=my-dataset
   anemoi-registry replica --list --list-format csv


*****************************
 Troubleshooting
*****************************

Unregistering a dataset
========================

Removing a dataset from the catalogue does **not** delete the actual
data.

**Known issue**: Reregistering a dataset
If you unregister a dataset and then try to register it again, you will get an error
hat the dataset already exists, even if it has been unregistered.
This is because the datasets are tracked by a unique identifier that is not deleted when the dataset is unregistered.

.. code-block:: bash

   # v2 only
   # fails if replicas still exist
   anemoi-registry dataset my-dataset --unregister