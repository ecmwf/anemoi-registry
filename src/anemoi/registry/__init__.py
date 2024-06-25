# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


import logging

from ._version import __version__ as __version__

LOG = logging.getLogger(__name__)


def config():
    from anemoi.utils.config import DotDict
    from anemoi.utils.config import load_config

    config = load_config().get("registry")
    if not config:
        LOG.warning(f"No 'registry' section in config. Config is {load_config()}. Limited functionalities.")
    return DotDict(config)
