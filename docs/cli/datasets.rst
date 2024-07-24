datasets
========

The `datasets` command is used to manage datasets in the registry.
It can be used to register or unregister a datasets, add and remove information about a dataset, and upload it to the catalogue.


The dataset names MUST follow the naming convention documented at <TODO ADD NAMING CONVENTION URL>.
For instance `dataset-name` can be `aifs-ea-an-oper-0001-mars-o96-1979-2022-6h-v6`.


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


*****************
Command line help
*****************

.. argparse::
    :module: anemoi.registry.__main__
    :func: create_parser
    :prog: anemoi-registry
    :path: datasets
