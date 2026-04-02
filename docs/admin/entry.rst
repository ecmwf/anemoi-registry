.. _admin-entry:

#######
 Entry
#######

.. warning::

   The ``entry`` command is a **low-level admin tool** for directly
   manipulating catalogue entries via the REST API. It bypasses the
   validation and safety checks of the higher-level commands. Use with
   caution.

The ``entry`` command allows dumping, loading, editing, and removing
arbitrary catalogue entries by their API path. It is useful for
debugging and for bulk catalogue operations.

This command is available in both v1 and v2.


*****************************
 Dumping an entry
*****************************

.. code-block:: bash

   # Print to stdout (JSON by default)
   anemoi-registry entry /datasets/my-dataset --dump

   # YAML output
   anemoi-registry entry /datasets/my-dataset --dump --yaml

   # Save to file
   anemoi-registry entry /datasets/my-dataset --dump --output entry.json


*****************************
 Loading (patching) an entry
*****************************

.. code-block:: bash

   # Update from a JSON file
   anemoi-registry entry /datasets/my-dataset --load --input updated.json

   # Create if it doesn't exist
   anemoi-registry entry /datasets/my-dataset --load --input new.json --create


*****************************
 Editing an entry
*****************************

Opens the entry in an editor (``$EDITOR`` or ``vi``), applies changes
as a JSON patch on save:

.. code-block:: bash

   anemoi-registry entry /datasets/my-dataset --edit
   anemoi-registry entry /datasets/my-dataset --edit --json
   anemoi-registry entry /datasets/my-dataset --edit --editor nano


*****************************
 Removing an entry
*****************************

.. code-block:: bash

   anemoi-registry entry /datasets/my-dataset --remove
