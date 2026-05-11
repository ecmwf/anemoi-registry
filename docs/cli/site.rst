site
====

.. note::

   This command is only available in CLI v2.
   Set ``ANEMOI_REGISTRY_CLI_VERSION=2`` to enable it.
   See :ref:`cli-versions`.

.. warning::

   The ``site`` command is experimental and intended for site
   administrators. Its interface may change in future versions.

The ``site`` command provides tooling for HPC site administrators to
monitor storage, report dataset replica status, and manage auxiliary
files.

Setup
-----

A one-time setup configures the local site against a catalogue server:

.. code-block:: bash

    anemoi-registry site --setup https://server/api/v1/sites/<site-name>

An interactive guided setup is also available:

.. code-block:: bash

    anemoi-registry site --setup-assistant

Monitoring
----------

These commands are designed to be run periodically (e.g. via cron):

.. code-block:: bash

    # Report quota and storage usage
    anemoi-registry site --storage

    # Report dataset replica status
    anemoi-registry site --datasets

    # Both at once
    anemoi-registry site --all

Use ``--dry-run`` to test without sending data to the server.

Auxiliary files
---------------

Download auxiliary files (grids, matrices, etc.) from remote storage:

.. code-block:: bash

    anemoi-registry site --update-auxiliary
