.. _anemoi-registry:

.. _index-page:

#############################################
 Welcome to `anemoi-registry` documentation!
#############################################

.. warning::

   This documentation is work in progress.

*Anemoi* is a framework for developing machine learning weather
forecasting models. It comprises of components or packages for preparing
training datasets, conducting ML model training and a registry for
datasets and trained models. *Anemoi* provides tools for operational
inference, including interfacing to verification software. As a
framework it seeks to handle many of the complexities that
meteorological organisations will share, allowing them to easily train
models from existing recipes but with their own data.

The ``anemoi-registry`` package provides a command-line tool and Python
API to interact with the Anemoi catalogue — a centralised registry for
datasets, trained models (weights), experiments, and training runs. It
also includes data-management tooling for HPC site administrators to
automate transfers, deletions, and storage monitoring.

**Overview**

The package provides:

- **Dataset management** — register, upload, and track datasets across
  multiple sites.
- **Model (weights) management** — upload and download trained model
  checkpoints.
- **Experiment and training tracking** — register experiments and
  training runs, attach weights, plots, and archive metadata.
- **Site administration** — site-level tooling for automated dataset
  transfers, deletions, storage monitoring, and quota reporting.

.. _getting-started:

*****************************
 Getting started
*****************************

-  :doc:`installing`
-  :doc:`configuring`
-  :doc:`naming-conventions`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Getting started

   installing
   configuring
   naming-conventions

.. _how-to:

*****************************
 How-to guides
*****************************

-  :doc:`howto/dataset`
-  :doc:`howto/models`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: How-to guides

   howto/dataset
   howto/models

.. _workflow-tools:

*****************************
 Workflow & admin tools
*****************************

-  :doc:`admin/experiments`
-  :doc:`admin/training`
-  :doc:`admin/tasks`
-  :doc:`admin/update`
-  :doc:`data-management/steward`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Workflow & admin tools

   admin/experiments
   admin/training
   admin/tasks
   admin/update
   data-management/steward

*****************
 Anemoi packages
*****************

-  :ref:`anemoi-utils <anemoi-utils:index-page>`
-  :ref:`anemoi-transform <anemoi-transform:index-page>`
-  :ref:`anemoi-datasets <anemoi-datasets:index-page>`
-  :ref:`anemoi-models <anemoi-models:index-page>`
-  :ref:`anemoi-graphs <anemoi-graphs:index-page>`
-  :ref:`anemoi-training <anemoi-training:index-page>`
-  :ref:`anemoi-inference <anemoi-inference:index-page>`
-  :ref:`anemoi-registry <anemoi-registry:index-page>`

*********
 License
*********

*Anemoi* is available under the open source `Apache License`__.

.. __: http://www.apache.org/licenses/LICENSE-2.0.html
