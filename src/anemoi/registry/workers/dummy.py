# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging

from . import Worker

LOG = logging.getLogger(__name__)


class DummyWorker(Worker):
    name = "dummy"

    def __init__(self, arg, **kwargs):
        super().__init__(**kwargs)
        LOG.warning(f"Dummy worker initialized with kwargs:{kwargs} and args:{arg}")

    def worker_process_task(self, task):
        LOG.warning(f"Dummy worker processing task={task}")
