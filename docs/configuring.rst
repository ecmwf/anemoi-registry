.. _configuring:

#############
 Configuring
#############

.. _cli-versions:

***************************
 CLI versions (v1 and v2)
***************************

The ``anemoi-registry`` CLI exists in two versions. The version is
controlled by the ``ANEMOI_REGISTRY_CLI_VERSION`` environment variable.

- **v1** (default): The original CLI. This is the default and requires no
  configuration. Set ``ANEMOI_REGISTRY_CLI_VERSION=1`` or leave unset.

- **v2** (recommended for new workflows): A restructured CLI with new
  commands (``replica``, ``steward``) and simplified singular command
  names (``dataset``, ``experiment``, ``training``, ``model``).
  Set ``ANEMOI_REGISTRY_CLI_VERSION=2`` to enable it.

.. code-block:: bash

   # Use v2 (recommended)
   export ANEMOI_REGISTRY_CLI_VERSION=2

   # Use v1 (default, can be omitted)
   export ANEMOI_REGISTRY_CLI_VERSION=1

.. note::

   The ``ANEMOI_REGISTRY_CLI_VERSION`` environment variable will be
   removed in a future release, when v2 becomes the only version.
   Existing v1 workflows will continue to work until then.

***************************
 Configuration files
***************************

The following configuration files are used to store the registry
configuration. These files allow configuring the catalogue urls, s3
buckets, API token and object storage credentials.

The first config file is ``~/.config/anemoi/settings.toml``. All keys in
this file are optional and have default values.

.. code::

   [registry]
   api_url = "https://anemoi.ecmwf.int/api/v1"

The second config file is ``~/.config/anemoi/settings.secrets.toml``.
This file must have the right permissions set to avoid unauthorized
access (`chmod 600 <filename>`). All keys in this file have no default
values. For users wanting to download data from the S3 storage they will
need to provide the following:

.. code::

   [object-storage]
   endpoint_url = "https://xxxxxxxxxxxx.xxx"
   aws_access_key_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   aws_secret_access_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

For users needing to interact with the catalogue, e.g. register a
dataset, they will also require the following in this second config
file:

.. code::

   [registry]
   api_token = "xxxxxxxxxxx"

***************************
 Viewing current settings
***************************

Use the ``settings`` command to display the effective configuration.
This is useful for debugging connection or authentication issues:

.. code-block:: bash

   anemoi-registry settings

   # Include secrets (tokens, keys) in the output
   anemoi-registry settings --show-secrets
