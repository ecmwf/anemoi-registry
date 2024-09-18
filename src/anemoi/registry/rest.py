# (C) Copyright 2023 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

import datetime
import logging
import os
import socket
from getpass import getuser

import requests
from requests.exceptions import HTTPError

from anemoi.registry import config

from ._version import __version__

LOG = logging.getLogger(__name__)

"""~/.aws/credentials

[default]
endpoint_url = https://object-store.os-api.cci1.ecmwf.int
aws_access_key_id=xxx
aws_secret_access_key=xxxx

"""


class AlreadyExists(ValueError):
    pass


def tidy(d):
    if isinstance(d, dict):
        return {k: tidy(v) for k, v in d.items()}

    if isinstance(d, list):
        return [tidy(v) for v in d if v is not None]

    # jsonschema does not support datetime.date
    if isinstance(d, datetime.datetime):
        return d.isoformat()

    if isinstance(d, datetime.date):
        return d.isoformat()

    return d


def trace_info():
    trace = {}
    trace["user"] = getuser()
    trace["host"] = socket.gethostname()
    trace["pid"] = os.getpid()
    trace["version"] = __version__
    return trace


class Rest:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        for k, v in trace_info().items():
            self.session.headers.update({f"x-anemoi-registry-{k}": str(v)})

    @property
    def token(self):
        return config().api_token

    def get(self, path, params=None, errors={}):
        self.log_debug("GET", path, params)

        kwargs = dict()
        if params is not None:
            kwargs["params"] = params

        r = self.session.get(f"{config().api_url}/{path}", **kwargs)
        self.raise_for_status(r, errors=errors)
        return r.json()

    def exists(self, *args, **kwargs):
        try:
            self.get(*args, **kwargs)
            return True
        except HTTPError as e:
            if e.response.status_code == 404:
                return False

    def put(self, path, data, errors={}):
        self.log_debug("PUT", path, data)
        if not data:
            raise ValueError(f"PUT data must be provided for {path}")
        r = self.session.put(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def patch(self, path, data, errors={}):
        self.log_debug("PATCH", path, data)
        if not data:
            raise ValueError(f"PATCH data must be provided for {path}")
        r = self.session.patch(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def post(self, path, data, errors={}):
        r = self.session.post(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def delete(self, path, errors={}):
        if not config().get("allow_delete"):
            raise ValueError("Unregister not allowed")
        return self.unprotected_delete(path, errors=errors)

    def unprotected_delete(self, path, errors={}):
        r = self.session.delete(f"{config().api_url}/{path}", params=dict(force=True))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def log_debug(self, verb, collection, data):
        if len(str(data)) > 100:
            if isinstance(data, dict):
                data = {k: "..." for k, v in data.items()}
            else:
                data = str(data)[:100] + "..."
        LOG.debug(f"{verb} {collection} {data}")

    def trace_info_dict(self):
        return dict(_trace_info=self.trace_info())

    def raise_for_status(self, r, errors={}):
        try:
            r.raise_for_status()
        except HTTPError as e:
            # add the response text to the exception message
            text = r.text
            text = text[:1000] + "..." if len(text) > 1000 else text
            e.args = (f"{e.args[0]} : {text}",)

            exception_handler = errors.get(e.response.status_code)
            errcode = e.response.status_code
            LOG.debug("HTTP error: ", errcode, exception_handler)
            if exception_handler:
                raise exception_handler(e)
            else:
                raise e


class RestItem:
    def __init__(self, collection, key):
        self.collection = collection
        self.key = key
        self.rest = Rest()
        self.path = f"{collection}/{key}"

    def exists(self):
        try:
            self.get()
            return True
        except HTTPError as e:
            if e.response.status_code == 404:
                return False

    def get(self, params=None, errors={}):
        return self.rest.get(self.path, params=params, errors=errors)

    def patch(self, data):
        return self.rest.patch(self.path, data)

    def put(self, data):
        return self.rest.put(self.path, data)

    def delete(self):
        return self.rest.delete(self.path)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.collection}, {self.key})"


class RestItemList:
    def __init__(self, collection):
        self.collection = collection
        self.rest = Rest()
        self.path = collection

    def get(self, params=None, errors={}):
        return self.rest.get(self.path, params=params, errors=errors)

    def post(self, data):
        return self.rest.post(self.path, data, errors={409: AlreadyExists})

    def __repr__(self):
        return f"{self.__class__.__name__}({self.collection})"
