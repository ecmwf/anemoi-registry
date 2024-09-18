############
 Installing
############

To install the package, you can use the following command:

.. code:: bash

   pip install anemoi-registry[...options...]

The options are:

-  ``dev``: install the development dependencies
-  ``all``: install all the dependencies
-  ``s3``: install the dependencies for S3 support

When you install the `anemoi-registry` package, this will also install
command line tool called ``anemoi-registry`` which can be used to manage
an anemoi catalogue.

**************
 Contributing
**************

.. code:: bash

   git clone ...
   cd anemoi-registry
   pip install .[dev]
   pip install -r docs/requirements.txt

You may also have to install pandoc on MacOS:

.. code:: bash

   brew install pandoc
