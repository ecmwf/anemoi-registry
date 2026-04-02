.. _admin-tasks:

#######
 Tasks
#######

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

   # Long output
   anemoi-registry task --list -l


*****************************
 Creating a task
*****************************

.. warning::

   The ``task`` command is a **low-level admin tool**. Normal users
   should not need to interact with tasks directly. Use the
   higher-level ``dataset``, ``replica``, and ``steward`` commands
   instead.

.. code-block:: bash

   anemoi-registry task --register action=transfer-dataset dataset=my-dataset destination=lumi source=ewc


*****************************
 Deleting a task
*****************************

.. warning::

   The ``task`` command is a **low-level admin tool**. Normal users
   should not need to interact with tasks directly. Use the
   higher-level ``dataset``, ``replica``, and ``steward`` commands
   instead.

.. code-block:: bash

   anemoi-registry task 12345678-1234-1234-1234-123456789abc --unregister
