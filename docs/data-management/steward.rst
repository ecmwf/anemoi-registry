.. _data-management-steward:

#################
 Steward command
#################

The ``steward`` command is the main entry point for site administration
and data management tasks. It is only available in **v2**
(``ANEMOI_REGISTRY_CLI_VERSION=2``).

.. warning::

   The ``steward`` command is intended for **site administrators** and
   automated infrastructure (e.g. ecflow suites). Normal users should
   not need to run these commands directly.


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
(e.g. via cron or ecflow):

.. code-block:: bash

   # Run all checks
   anemoi-registry steward monitor

   # Storage quota only
   anemoi-registry steward monitor --storage

   # Dataset replica status only
   anemoi-registry steward monitor --datasets

   # Dry run (do not send data to the server)
   anemoi-registry steward monitor --dry-run


*****************************
 Updates
*****************************

Run local update operations:

.. code-block:: bash

   # Run all updates
   anemoi-registry steward update

   # Download auxiliary files (grids, matrices, etc.)
   anemoi-registry steward update --auxiliary

   # Re-fetch the shared site config from the server
   anemoi-registry steward update --shared-config

   # Synchronise zarr metadata for all local replicas
   anemoi-registry steward update --datasets

   # Dry run
   anemoi-registry steward update --datasets --dry-run


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

Tasks are created by user-facing commands such as ``replica
--request-delete`` or ``replica --request-transfer``.


*****************************
 Migrating from v1
*****************************

In v1, the equivalent functionality was split across the ``worker`` and
``site`` commands:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   -  -  v1
      -  v2

   -  -  ``anemoi-registry worker transfer-dataset ...``
      -  ``anemoi-registry steward run-task action=transfer-dataset ...``

   -  -  ``anemoi-registry worker delete-dataset ...``
      -  ``anemoi-registry steward run-task action=delete-dataset ...``

   -  -  ``anemoi-registry site --setup URL``
      -  ``anemoi-registry steward --site SITE setup``

   -  -  ``anemoi-registry site --storage``
      -  ``anemoi-registry steward monitor --storage``

   -  -  ``anemoi-registry site --datasets``
      -  ``anemoi-registry steward monitor --datasets``

   -  -  ``anemoi-registry site --update-auxiliary``
      -  ``anemoi-registry steward update --auxiliary``

   -  -  ``anemoi-registry update -Z FILE``
      -  ``anemoi-registry steward update --datasets``
