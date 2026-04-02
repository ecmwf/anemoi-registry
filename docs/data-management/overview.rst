.. _data-management-overview:

############################
 Data management overview
############################

The ``anemoi-registry`` package includes data management tooling for
HPC site administrators to automate dataset lifecycle operations —
transfers, deletions, storage monitoring, and metadata synchronisation.

.. note::

   The data management features require **v2** of the CLI.
   See :ref:`cli-versions`.

   .. code-block:: bash

      export ANEMOI_REGISTRY_CLI_VERSION=2


*****************************
 Key concepts
*****************************

Sites
======

A **site** represents a physical location where datasets can be stored
— for example, an HPC centre (``ewc``, ``lumi``, ``leonardo``), a
cloud storage bucket, or a local filesystem. Each site is registered in
the catalogue with its own configuration including storage paths,
quota monitoring commands, and task runner settings.

Dataset lifecycle
==================

A dataset goes through several stages:

1. **Created** — a dataset is built locally using ``anemoi-datasets``.
2. **Registered** — metadata is pushed to the catalogue
   (``anemoi-registry dataset --register``).
3. **Replicated** — copies are uploaded or transferred to one or more
   sites (``anemoi-registry replica SITE NAME --upload``).
4. **Active** — the dataset is in use for training or inference.
5. **Retired** — the dataset is no longer needed and replicas can be
   deleted.

Tasks and the task runner
==========================

Certain operations (transfers, deletions) are handled asynchronously
via a **task queue** in the catalogue. Users or automated tools create
tasks (e.g. ``replica --request-delete`` or ``replica
--request-transfer``), and a **task runner** (the ``steward run-task``
command) claims and executes them.

This decouples the request from the execution, allowing transfers and
deletions to be handled by site-specific infrastructure (e.g. an ecflow
suite).

.. warning::

   Normal users should not interact with tasks directly. Use the
   higher-level ``dataset`` and ``replica`` commands to request
   operations. Tasks are an implementation detail managed by site
   administrators.


*****************************
 Monitoring
*****************************

Storage quota
==============

The steward can report storage quota and usage for the site:

.. code-block:: bash

   anemoi-registry steward monitor --storage

This runs site-specific quota commands (configured in the site's
bootstrap config) and reports the results to the catalogue.

Dataset replica status
=======================

The steward can check the status of all local replicas (e.g. whether
files still exist, last access times):

.. code-block:: bash

   anemoi-registry steward monitor --datasets

Both checks at once:

.. code-block:: bash

   anemoi-registry steward monitor


*****************************
 Updating metadata
*****************************

Synchronise zarr metadata for all local replicas from the catalogue:

.. code-block:: bash

   anemoi-registry steward update --datasets

This iterates over all replicas registered at the local site and
updates each zarr file's metadata from the catalogue.

Download auxiliary files (grids, matrices, etc.):

.. code-block:: bash

   anemoi-registry steward update --auxiliary

Re-fetch the shared site configuration:

.. code-block:: bash

   anemoi-registry steward update --shared-config

Run all updates at once:

.. code-block:: bash

   anemoi-registry steward update


*****************************
 Automated tasks
*****************************

Dataset transfers
==================

Transfers between sites are created as tasks, then executed by the task
runner:

.. code-block:: bash

   # Request a transfer (creates a task in the catalogue)
   anemoi-registry replica lumi my-dataset --request-transfer ewc

   # The task runner picks it up (on the destination site)
   anemoi-registry steward run-task action=transfer-dataset destination=lumi

Dataset deletions
==================

.. code-block:: bash

   # Request deletion (creates a task)
   anemoi-registry replica ewc my-dataset --request-delete

   # The task runner picks it up
   anemoi-registry steward run-task action=delete-dataset
