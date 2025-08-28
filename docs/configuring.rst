.. _configuring:

#############
 Configuring
#############

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
