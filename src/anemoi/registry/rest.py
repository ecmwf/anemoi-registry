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
import sys
from getpass import getuser

import requests
from requests.exceptions import HTTPError

from anemoi.registry import config
from anemoi.registry._version import version

LOG = logging.getLogger(__name__)
# LOG.setLevel(logging.DEBUG)

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


class BaseRest:
    def __init__(self):
        self.config = config()

    def get(self, collection):
        LOG.debug(f"GET {collection}")
        try:
            r = requests.get(f"{self.config.api_url}/{collection}", headers={"Authorization": f"Bearer {self.token}"})
            self.raise_for_status(r)
            return r.json()
        except Exception as e:
            LOG.error(e)
            raise (e)

    def post(self, collection, data):
        LOG.debug(f"POST {collection} { {k:'...' for k,v in data.items()} }")

    def patch(self, collection, data):
        LOG.debug(f"PATCH {collection} {data}")

    def put(self, collection, data):
        LOG.debug(f"PUT {collection} {data}")

    def delete(self, collection):
        LOG.debug(f"DELETE {collection}")

    def trace_info(self):
        trace = {}
        trace["tool_path"] = __file__
        trace["tool_cmd"] = sys.argv
        trace["user"] = getuser()
        trace["host"] = socket.gethostname()
        trace["pid"] = os.getpid()
        trace["timestamp"] = datetime.datetime.now().isoformat()
        trace["version"] = version
        return trace

    def trace_info_dict(self):
        return dict(_trace_info=self.trace_info())

    @property
    def token(self):
        return self.config.api_token

    def raise_for_status(self, r):
        try:
            r.raise_for_status()
        except HTTPError as e:
            # add the response text to the exception message
            text = r.text
            text = text[:1000] + "..." if len(text) > 1000 else text
            e.args = (f"{e.args[0]} : {text}",)
            raise e


class ReadOnlyRest(BaseRest):
    pass


class Rest(BaseRest):
    def raise_for_status(self, r):
        try:
            r.raise_for_status()
        except HTTPError as e:
            # add the response text to the exception message
            text = r.text
            text = text[:1000] + "..." if len(text) > 1000 else text
            e.args = (f"{e.args[0]} : {text}",)
            raise e

    def post(self, collection, data):
        super().post(collection, data)
        try:
            r = requests.post(
                f"{self.config.api_url}/{collection}",
                json=tidy(data),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.raise_for_status(r)
            return r.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                raise AlreadyExists(f"{e}Already exists in {collection}")
            else:
                LOG.error(f"Error in post to {collection} with data:{data}")
                LOG.error(e)
                raise
        except Exception as e:
            LOG.error(f"Error in post to {collection} with data:{data}")
            LOG.error(e)
            raise

    def patch(self, collection, data):
        super().patch(collection, data)
        try:
            r = requests.patch(
                f"{self.config.api_url}/{collection}",
                json=tidy(data),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.raise_for_status(r)
            return r.json()
        except Exception as e:
            LOG.error(e)
            raise (e)

    def put(self, collection, data):
        super().put(collection, data)
        try:
            r = requests.put(
                f"{self.config.api_url}/{collection}",
                json=tidy(data),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.raise_for_status(r)
            return r.json()
        except Exception as e:
            LOG.error(e)
            raise (e)

    def delete(self, collection):
        super().delete(collection)
        try:
            r = requests.delete(
                f"{self.config.api_url}/{collection}", headers={"Authorization": f"Bearer {self.token}"}
            )
            self.raise_for_status(r)
            return r.json()
        except Exception as e:
            LOG.error(e)
            raise (e)
