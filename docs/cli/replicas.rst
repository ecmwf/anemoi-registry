replicas
========

.. note::

   This command is only available in CLI v2.
   Set ``ANEMOI_REGISTRY_CLI_VERSION=2`` to enable it.
   See :ref:`cli-versions`.

The ``replica`` command manages dataset locations (replicas) across
sites. It replaces the ``datasets --add-location`` / ``--remove-location``
flags from v1.

.. _datasets-vs-replicas:

Datasets vs replicas
--------------------

A **dataset** is a unique entry in the catalogue. It has a name, metadata
(recipe, status, etc.), and is created once.

A **replica** is a copy of a dataset stored at a specific site. A single
dataset can have multiple replicas across different sites (e.g. one on
S3, one on a local Lustre filesystem). Replicas track where the data
physically lives.

In v1, replicas were managed as "locations" within the ``datasets``
command. In v2, this is a dedicated command for clarity.

Registering a replica
---------------------

Register a local dataset copy as a replica on a site:

.. code-block:: bash

    anemoi-registry replica --register /path/to/dataset-name.zarr --site ewc

To upload the data at the same time:

.. code-block:: bash

    anemoi-registry replica --register /path/to/dataset-name.zarr --site ewc --upload

A custom URI pattern can be provided:

.. code-block:: bash

    anemoi-registry replica --register /path/to/dataset-name.zarr --site ewc \
        --uri-pattern 's3://ml-datasets/{name}.zarr'

Removing a replica
------------------

Remove a replica from the catalogue without deleting the data:

.. code-block:: bash

    anemoi-registry replica --unregister --dataset-name dataset-name --site ewc

Delete the data and remove the catalogue entry:

.. code-block:: bash

    anemoi-registry replica --delete --dataset-name dataset-name --site ewc

Listing replicas
----------------

List all replicas, optionally filtered:

.. code-block:: bash

    anemoi-registry replica --list
    anemoi-registry replica --list site=ewc
    anemoi-registry replica --list --list-format csv
