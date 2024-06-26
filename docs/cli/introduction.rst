Introduction
============

When you install the `anemoi-registry` package, this will also install command line tool
called ``anemoi-registry`` which can be used to manage the registry.

The tool can provide help with the ``--help`` options:

.. code-block:: bash

    % anemoi-registry --help

The commands are:

.. toctree::
    :maxdepth: 1

    list
    datasets
    experiments
    weights

.. argparse::
    :module: anemoi.registry.__main__
    :func: create_parser
    :prog: anemoi-registry
    :nosubcommands:
