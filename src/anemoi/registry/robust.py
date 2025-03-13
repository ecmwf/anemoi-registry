# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import logging
import time

import requests

LOG = logging.getLogger(__name__)

RETRIABLE = (
    requests.codes.internal_server_error,
    requests.codes.bad_gateway,
    requests.codes.service_unavailable,
    requests.codes.gateway_timeout,
    requests.codes.too_many_requests,
    requests.codes.request_timeout,
)


def make_robust(call: callable, maximum_tries: int = 60, retry_after: int = 60) -> callable:
    """Retry a function call in case of connection errors or HTTP errors.

    Parameters
    ----------
    call : callable
        function to call
    maximum_tries : int, optional
        maximum number of retries, by default 60
    retry_after : int, optional
        seconds to wait between retries, by default 60

    Returns
    -------
    callable
        A wrapped function that retries the call in case of specified errors.
    """

    def retriable(code):
        return code in RETRIABLE

    def wrapped(url, *args, **kwargs):
        tries = 0
        main_url = url

        while True:
            tries += 1

            if tries >= maximum_tries:
                # Last attempt, don't do anything
                return call(main_url, *args, **kwargs)

            try:
                r = call(main_url, *args, **kwargs)
            except requests.exceptions.SSLError:
                raise
            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
            ) as e:
                r = None
                LOG.warning(
                    "Recovering from connection error [%s], attemps %s of %s",
                    e,
                    tries,
                    maximum_tries,
                )

            if r is not None:
                if not retriable(r.status_code):
                    return r
                LOG.warning(
                    "Recovering from HTTP error [%s %s], attemps %s of %s",
                    r.status_code,
                    r.reason,
                    tries,
                    maximum_tries,
                )

            LOG.warning("Retrying in %s seconds", retry_after)
            time.sleep(retry_after)
            LOG.info("Retrying now...")

    return wrapped
