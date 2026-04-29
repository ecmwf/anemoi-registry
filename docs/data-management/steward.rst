.. _data-management:

#################
 Data management
#################

The ``anemoi-registry`` package includes data management tooling for
HPC site administrators to automate dataset lifecycle operations —
transfers, deletions, storage monitoring, and metadata synchronisation.

These features are available through the ``steward`` command
(``ANEMOI_REGISTRY_CLI_VERSION=2``).

.. warning::

   The ``steward`` command is intended for **site administrators** and
   automated infrastructure (e.g. ecflow suites). Normal users should
   not need to run these commands directly.


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
 Initial setup
*****************************

Before using the steward, run a one-time bootstrap to configure the
local site:

.. code-block:: bash

   # From a site name (resolves to the catalogue server)
   anemoi-registry steward --site ewc setup

   # From a URL
   anemoi-registry steward --site https://anemoi.ecmwf.int/api/v1/sites/ewc/config setup

   # From a local file
   anemoi-registry steward --site /path/to/config.toml setup

This writes a ``steward.json`` file that stores the site's bootstrap
configuration.


*****************************
 Viewing configuration
*****************************

.. code-block:: bash

   # Print the effective config as JSON
   anemoi-registry steward config

   # Override the site for this invocation
   anemoi-registry steward --site ewc config


*****************************
 Monitoring
*****************************

Report site status to the catalogue. Designed to be run periodically
(e.g. via cron or ecflow).

Storage quota
==============

.. code-block:: bash

   anemoi-registry steward monitor --storage

This runs site-specific quota commands (configured in the site's
bootstrap config) and reports the results to the catalogue.

Dataset replica status
=======================

Check the status of all local replicas (e.g. whether files still exist,
last access times):

.. code-block:: bash

   anemoi-registry steward monitor --datasets

Both checks at once:

.. code-block:: bash

   anemoi-registry steward monitor

Use ``--dry-run`` to preview without sending data to the server.


*****************************
 Updates
*****************************

Run local update operations.

Synchronise zarr metadata
==========================

Update zarr metadata for all local replicas from the catalogue:

.. code-block:: bash

   anemoi-registry steward update --datasets

Auxiliary files
================

Download auxiliary files (grids, matrices, etc.):

.. code-block:: bash

   anemoi-registry steward update --auxiliary

Shared configuration
=====================

Re-fetch the shared site configuration from the server:

.. code-block:: bash

   anemoi-registry steward update --shared-config

Run all updates at once:

.. code-block:: bash

   anemoi-registry steward update

Use ``--dry-run`` to preview without making changes.


*****************************
 Running tasks
*****************************

Claim and execute a queued task from the catalogue. This is designed to
be called from an ecflow job or similar scheduler:

.. code-block:: bash

   # Run the next queued task matching the filters
   anemoi-registry steward run-task action=transfer-dataset destination=lumi

   # Run a specific task by UUID
   anemoi-registry steward run-task uuid=12345678-1234-1234-1234-123456789abc

   # Override number of transfer threads
   anemoi-registry steward run-task action=transfer-dataset --threads 4

   # Dry run
   anemoi-registry steward run-task action=transfer-dataset --dry-run


*****************************
 Automated transfers
*****************************

Transfers between sites are created as tasks, then executed by the task
runner:

.. code-block:: bash

   # Request a transfer (creates a task in the catalogue)
   anemoi-registry replica lumi my-dataset --request-transfer ewc

   # The task runner picks it up (on the destination site)
   anemoi-registry steward run-task action=transfer-dataset destination=lumi


*****************************
 Automated deletions
*****************************

.. code-block:: bash

   # Request deletion (creates a task)
   anemoi-registry replica ewc my-dataset --request-delete

   # The task runner picks it up
   anemoi-registry steward run-task action=delete-dataset
