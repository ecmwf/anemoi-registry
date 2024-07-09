#############
 Configuring
#############

The following configuration files are used to store the registry
configuration. These files allow configuring the catalogue urls, s3
buckets, API token and object storage credentials.

The first config file is ``~/.config/anemoi/config.toml``.

.. code::

   [registry]
   api_url = "https://anemoi.ecmwf.int/api/v1"                 # Required

   plots_uri_pattern = "s3://ml-artefacts/{expver}/{basename}" # Optional
   datasets_uri_pattern = "s3://ml-datasets/{name}"            # Optional
   weights_uri_pattern = "s3://ml-weights/{uuid}.ckpt"         # Optional
   weights_platform = "ewc"                                    # Optional

The second config file is ``~/.config/anemoi/config.secret.toml``. This
file should have the right permissions set to avoid unauthorized access
(`chmod 600 <filename>`). All keys are required.

.. code::

   [registry]
   api_token = "xxxxxxxxxxx"

   [object-storage]
   endpoint_url = "https://xxxxxxxxxxxx.xxx"
   aws_access_key_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   aws_secret_access_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
