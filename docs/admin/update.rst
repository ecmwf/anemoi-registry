.. _admin-update:

########
 Update
########

The ``update`` command synchronises metadata between dataset recipe
files, catalogue entries, and zarr datasets. It is primarily used by
administrators to keep the catalogue consistent.

This command is available in both v1 and v2.


*************************************************
 Update catalogue from recipe files
*************************************************

Updates catalogue entries with the latest metadata derived from recipe
files. This creates a temporary minimal dataset to extract current
metadata values.

.. code-block:: bash

   # Update single recipe
   anemoi-registry update --catalogue-from-recipe-file recipe.yaml

   # Update multiple recipes
   anemoi-registry update --catalogue-from-recipe-file *.yaml

   # Preview changes without applying them
   anemoi-registry update --catalogue-from-recipe-file recipe.yaml --dry-run

   # Force update of existing entries
   anemoi-registry update --catalogue-from-recipe-file --force --update *.yaml

   # Specify a working directory for temporary datasets
   anemoi-registry update --catalogue-from-recipe-file --workdir /tmp *.yaml

.. note::

   The ``--set-recipe`` flag on the ``dataset`` command is deprecated.
   Use ``update --catalogue-from-recipe-file`` instead.


*************************************************
 Update zarr files from catalogue (v1 only)
*************************************************

Synchronises zarr metadata with the corresponding catalogue entry.

.. code-block:: bash

   anemoi-registry update --zarr-file-from-catalogue dataset.zarr

   # With progress tracking
   anemoi-registry update --zarr-file-from-catalogue --progress progress.txt data/*.zarr

.. note::

   In v2, this functionality has moved to
   ``anemoi-registry steward update --datasets``, which automatically
   processes all local replicas.
