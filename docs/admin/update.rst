.. _admin-update:

#########################
 Update dataset metadata
#########################

.. note::

   The ``update`` command is available in **v2 only**.

The ``update`` command synchronises metadata between dataset recipe
files, catalogue entries, and zarr datasets. It is primarily used by
administrators to keep the catalogue consistent.

*************************************************
 Update zarr metadata from catalogue
*************************************************

Updates the metadata stored inside local zarr files to match the
current catalogue entry. Each zarr file must contain a ``uuid``
attribute which is used to look up the corresponding catalogue entry.
The catalogue metadata is then written into the zarr file's attributes.

.. code-block:: bash

   # Update a single zarr file
   anemoi-registry update --metadata-from-catalogue /data/anemoi/datasets/my-dataset.zarr

   # Update several zarr files at once
   anemoi-registry update --metadata-from-catalogue /data/anemoi/datasets/*.zarr

   # Preview changes without writing
   anemoi-registry update --metadata-from-catalogue /data/anemoi/datasets/my-dataset.zarr --dry-run

   # Continue to the next file on error
   anemoi-registry update --metadata-from-catalogue /data/anemoi/datasets/*.zarr --continue
