.. _howto-datasets:

##########
 Datasets
##########

This guide covers how to register, manage, and troubleshoot datasets in
the Anemoi catalogue.

.. note::

   The ``dataset`` command exists in two CLI versions. **v2 is
   recommended** for new workflows. See :ref:`cli-versions` for how to
   switch. Throughout this guide, v2 commands are shown first, with v1
   equivalents noted where they differ.

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

v2 (recommended)
=================

.. code-block:: bash

   # Register — NAME is deduced from the path basename
   anemoi-registry dataset --register /path/to/my-dataset.zarr

   # Or provide the name explicitly
   anemoi-registry dataset my-dataset --register /path/to/my-dataset.zarr

   # Register and set metadata at the same time
   anemoi-registry dataset --register /path/to/my-dataset.zarr \
       --set-status experimental

v1 (legacy)
============

.. code-block:: bash

   anemoi-registry datasets /path/to/my-dataset.zarr --register

   # With metadata
   anemoi-registry datasets /path/to/my-dataset.zarr --register \
       --set-recipe ./recipe.yaml --set-status experimental


Write credentials are required. See :ref:`configuring`.


*****************************
 Viewing a dataset
*****************************

.. code-block:: bash

   # v2
   anemoi-registry dataset my-dataset

   # v1
   anemoi-registry datasets my-dataset


*****************************
 Working with metadata
*****************************

v2 (recommended)
=================

.. code-block:: bash

   # Get a metadata value
   anemoi-registry dataset my-dataset --metadata get status

   # Set a metadata value
   anemoi-registry dataset my-dataset --metadata set status=active

   # Delete a metadata key
   anemoi-registry dataset my-dataset --metadata delete some_key

   # Set status shortcut
   anemoi-registry dataset my-dataset --set-status active

v1 (legacy)
============

.. code-block:: bash

   anemoi-registry datasets my-dataset --get-metadata status
   anemoi-registry datasets my-dataset --set-metadata status active
   anemoi-registry datasets my-dataset --remove-metadata some_key
   anemoi-registry datasets my-dataset --set-status active


*****************************
 Uploading a dataset to S3
*****************************

Once the dataset is registered in the catalogue, you can upload the data
to a remote site and register the replica.

v2 (recommended)
=================

In v2, uploading and managing replicas is done through the ``replica``
command:

.. code-block:: bash

   # Upload to a site (e.g. ewc) — registers the replica automatically
   anemoi-registry replica ewc my-dataset --upload /path/to/my-dataset.zarr

   # Register a replica without uploading (data already present at site)
   anemoi-registry replica ewc my-dataset --register /path/on/site/my-dataset.zarr

   # With a custom target URI
   anemoi-registry replica ewc my-dataset --upload /path/to/my-dataset.zarr \
       --target-uri 's3://my-bucket/{name}.zarr'

S3 credentials are required. See :ref:`configuring`.

v1 (legacy)
============

.. code-block:: bash

   anemoi-registry datasets /path/to/my-dataset.zarr --add-location ewc --upload


*****************************
 Listing datasets
*****************************

.. code-block:: bash

   # v2
   anemoi-registry dataset --list
   anemoi-registry dataset --list status=active

   # v1 (uses the 'list' command)
   anemoi-registry list datasets


*****************************
 Listing replicas
*****************************

v2 only:

.. code-block:: bash

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

.. code-block:: bash

   # v2 — fails if replicas still exist
   anemoi-registry dataset my-dataset --unregister

   # Force unregister even with existing replicas
   anemoi-registry dataset my-dataset --unregister -f

   # v1
   anemoi-registry datasets my-dataset --unregister

Removing a replica
===================

.. code-block:: bash

   # Remove the catalogue entry only (data is kept)
   anemoi-registry replica ewc my-dataset --unregister

   # Schedule deletion of data + catalogue entry (via the task runner)
   anemoi-registry replica ewc my-dataset --request-delete

Requesting a transfer
======================

To schedule a transfer of a dataset from one site to another (handled by
the task runner):

.. code-block:: bash

   # Transfer my-dataset to lumi, sourcing from ewc
   anemoi-registry replica lumi my-dataset --request-transfer ewc
