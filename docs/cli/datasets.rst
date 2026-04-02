datasets
========

.. note::

   In v1, this command is called ``datasets`` (plural). In v2, it is
   ``dataset`` (singular). See :ref:`cli-versions` for how to switch.
   The v2 version is recommended for new workflows. In v2, location
   management has moved to the dedicated :doc:`replicas` command.

The ``datasets`` command is used to manage datasets in the registry.
It can be used to register or unregister a dataset, add metadata, and
upload it to the catalogue.

The dataset names MUST follow the naming convention documented at :ref:`naming-conventions`.
For instance `dataset-name` can be `aifs-ea-an-oper-0001-mars-o96-1979-2022-6h-v6`.

v2 (recommended)
----------------

Enable v2 by setting ``ANEMOI_REGISTRY_CLI_VERSION=2``. See :ref:`cli-versions`.

**Registering**

After creating locally a new dataset (using `anemoi-datasets`), registering it in the catalogue can be done as follows:

.. code-block:: bash

    anemoi-registry dataset --register /path/to/dataset-name.zarr

Write credentials are needed to register a dataset to the catalogue. See :ref:`configuring`.


**Adding metadata**

Additional information should be added to the dataset, such as the recipe used to create it, the status of the dataset.
This can be done as follow:

.. code-block:: bash

    anemoi-registry dataset --register /path/to/dataset-name.zarr --set-recipe ./recipe.yaml --set-status experimental


Alternatively, the metadata can be added to an existing dataset:

.. code-block:: bash

    anemoi-registry dataset dataset-name --set-recipe ./recipe.yaml
    anemoi-registry dataset dataset-name --set-status experimental


**Uploading to S3 and managing locations**

In v2, uploading and managing dataset locations (replicas) is done through the
:doc:`replicas` command instead of ``datasets --add-location``.

.. code-block:: bash

    anemoi-registry replica --register /path/to/dataset-name.zarr --site ewc --upload

See :doc:`replicas` for details.

v1 (legacy)
-----------

This is the default when ``ANEMOI_REGISTRY_CLI_VERSION`` is unset or set to ``1``.

**Registering**

After creating locally a new dataset (using `anemoi-datasets`), registering it in the catalogue can be done as follow:

.. code-block:: bash

    anemoi-registry datasets /path/to/dataset-name.zarr --register

Write credentials are needed to register a dataset to the catalogue. See :ref:`configuring`.


**Adding metadata**

Additional information should be added to the dataset, such as the recipe used to create it, the status of the dataset,
and the location of the dataset.
This can be done as follow:

.. code-block:: bash

    anemoi-registry datasets /path/to/dataset-name.zarr --register --set-recipe ./recipe.yaml --set-status experimental


Alternatively, the metadata can be added to an existing dataset:

.. code-block:: bash

    anemoi-registry datasets dataset-name --set-recipe ./recipe.yaml
    anemoi-registry datasets dataset-name --set-status experimental


**Uploading to S3**

Uploading the dataset to the catalogue to S3 can be done as follow:

.. code-block:: bash

    anemoi-registry datasets /path/to/dataset-name.zarr --add-location ewc --upload

S3 credentials are required to upload a dataset, see :ref:`configuring`.
