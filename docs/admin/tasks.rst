.. _admin-tasks:

#######
 Tasks
#######

.. warning::

   The ``task`` command is a **low-level admin tool**. Normal users
   should not need to interact with tasks directly. Use the
   higher-level ``dataset``, ``replica``, and ``steward`` commands
   instead.

Tasks are the mechanism by which asynchronous operations (transfers,
deletions) are queued and executed. Each task has a UUID, an action
type, a status (``queued``, ``running``, ``completed``, ``failed``),
and associated metadata.

This command is only available in **v2**.

*****************************
 Listing tasks
*****************************

.. code-block:: bash

   # List all tasks
   anemoi-registry task --list

   # Filter by status
   anemoi-registry task --list status=queued

   # Filter by action
   anemoi-registry task --list action=transfer-dataset

   # Combine filters
   anemoi-registry task --list action=transfer-dataset status=queued

   # Output as CSV or JSON
   anemoi-registry task --list --list-format csv
   anemoi-registry task --list --list-format json

   # Custom fields
   anemoi-registry task --list --list-fields uuid,action,status,created

   # Long output
   anemoi-registry task --list -l


*****************************
 Creating a task
*****************************

.. code-block:: bash

   anemoi-registry task --register action=transfer-dataset dataset=my-dataset destination=lumi


*****************************
 Viewing a task
*****************************

.. code-block:: bash

   anemoi-registry task 12345678-1234-1234-1234-123456789abc


*****************************
 Deleting tasks
*****************************

.. code-block:: bash

   # Delete by UUID
   anemoi-registry task 12345678-1234-1234-1234-123456789abc --unregister

   # Delete by filter (asks for confirmation)
   anemoi-registry task --unregister action=dummy status=failed

   # Skip confirmation
   anemoi-registry task --unregister action=dummy status=failed -y
