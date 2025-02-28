# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
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


def trace_info() -> dict:
    """Collect trace information including user, host, process ID, and version.

    Returns
    -------
    dict
        A dictionary containing trace information.
    """
    trace = {}
    trace["user"] = getuser()
    trace["host"] = socket.gethostname()
    trace["pid"] = os.getpid()
    trace["version"] = __version__
    return trace


class Rest:
    """REST API client."""

    def __init__(self):
        """Initialize the REST API client."""
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        for k, v in trace_info().items():
            self.session.headers.update({f"x-anemoi-registry-{k}": str(v)})

    @property
    def token(self) -> str:
        """Get the API token from the configuration."""
        return config().api_token

    def get(self, path: str, params: dict = None, errors: dict = {}) -> dict:
        """Perform a GET request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        params : dict, optional
            The query parameters for the request.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        self.log_debug("GET", path, params)

        kwargs = dict()
        if params is not None:
            kwargs["params"] = params

        r = self.session.get(f"{config().api_url}/{path}", **kwargs)
        self.raise_for_status(r, errors=errors)
        return r.json()

    def exists(self, *args, **kwargs) -> bool:
        """Check if a resource exists.

        Parameters
        ----------
        *args : tuple
            Positional arguments to pass to the get method.
        **kwargs : dict
            Keyword arguments to pass to the get method.

        Returns
        -------
        bool
            True if the resource exists, False otherwise.
        """
        try:
            self.get(*args, **kwargs)
            return True
        except HTTPError as e:
            if e.response.status_code == 404:
                return False

    def put(self, path: str, data: dict, errors: dict = {}) -> dict:
        """Perform a PUT request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        data : dict
            The data to send in the request body.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        self.log_debug("PUT", path, data)
        if not data:
            raise ValueError(f"PUT data must be provided for {path}")
        r = self.session.put(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def patch(self, path: str, data: dict, errors: dict = {}) -> dict:
        """Perform a PATCH request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        data : dict
            The data to send in the request body.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        self.log_debug("PATCH", path, data)
        if not data:
            raise ValueError(f"PATCH data must be provided for {path}")
        r = self.session.patch(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def post(self, path: str, data: dict, errors: dict = {}) -> dict:
        """Perform a POST request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        data : dict
            The data to send in the request body.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        r = self.session.post(f"{config().api_url}/{path}", json=tidy(data))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def delete(self, path: str, errors: dict = {}) -> dict:
        """Perform a DELETE request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        if not config().get("allow_delete"):
            raise ValueError("Unregister not allowed")
        return self.unprotected_delete(path, errors=errors)

    def unprotected_delete(self, path: str, errors: dict = {}) -> dict:
        """Perform an unprotected DELETE request.

        Parameters
        ----------
        path : str
            The API endpoint path.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        r = self.session.delete(f"{config().api_url}/{path}", params=dict(force=True))
        self.raise_for_status(r, errors=errors)
        return r.json()

    def log_debug(self, verb: str, collection: str, data: dict) -> None:
        """Log debug information for a request.

        Parameters
        ----------
        verb : str
            The HTTP verb (e.g., GET, POST).
        collection : str
            The collection or endpoint being accessed.
        data : dict
            The data being sent or received.
        """
        if len(str(data)) > 100:
            if isinstance(data, dict):
                data = {k: "..." for k, v in data.items()}
            else:
                data = str(data)[:100] + "..."
        LOG.debug(f"{verb} {collection} {data}")

    def trace_info_dict(self) -> dict:
        """Get trace information as a dictionary.

        Returns
        -------
        dict
            A dictionary containing trace information.
        """
        return dict(_trace_info=self.trace_info())

    def raise_for_status(self, r: requests.Response, errors: dict = {}) -> None:
        """Raise an HTTPError if the response contains an HTTP error status code.

        Parameters
        ----------
        r : requests.Response
            The response object.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.
        """
        try:
            r.raise_for_status()
        except HTTPError as e:
            # add the response text to the exception message
            text = r.text
            text = text[:1000] + "..." if len(text) > 1000 else text
            e.args = (f"{e.args[0]} : {text}",)

            exception_handler = errors.get(e.response.status_code)
            errcode = e.response.status_code
            LOG.debug("HTTP error: %s %s", errcode, exception_handler)
            if exception_handler:
                raise exception_handler(e)
            else:
                raise e


class RestItem:
    """Single catalogue entry from REST API."""

    def __init__(self, collection: str, key: str):
        """Initialize a RestItem.

        Parameters
        ----------
        collection : str
            The collection name.
        key : str
            The key of the item.
        """
        self.collection = collection
        self.key = key
        self.rest = Rest()
        self.path = f"{collection}/{key}"

    def exists(self) -> bool:
        """Check if the item exists.

        Returns
        -------
        bool
            True if the item exists, False otherwise.
        """
        try:
            self.get()
            return True
        except HTTPError as e:
            if e.response.status_code == 404:
                return False

    def get(self, params: dict = None, errors: dict = {}) -> dict:
        """Retrieve the item.

        Parameters
        ----------
        params : dict, optional
            The query parameters for the request.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.get(self.path, params=params, errors=errors)

    def patch(self, data: dict) -> dict:
        """Update the item with a PATCH request.

        Parameters
        ----------
        data : dict
            The data to send in the request body.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.patch(self.path, data)

    def put(self, data: dict) -> dict:
        """Update the item with a PUT request.

        Parameters
        ----------
        data : dict
            The data to send in the request body.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.put(self.path, data)

    def delete(self) -> dict:
        """Delete the item.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.delete(self.path)

    def unprotected_delete(self) -> dict:
        """Delete the item without protection.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.unprotected_delete(self.path)

    def __repr__(self) -> str:
        """Return a string representation of the RestItem."""
        return f"{self.__class__.__name__}({self.collection}, {self.key})"


class RestItemList:
    """List of catalogue entries from REST API."""

    def __init__(self, collection: str):
        """Initialize a RestItemList.

        Parameters
        ----------
        collection : str
            The collection name.
        """
        self.collection = collection
        self.rest = Rest()
        self.path = collection

    def get(self, params: dict = None, errors: dict = {}) -> dict:
        """Retrieve the list of items.

        Parameters
        ----------
        params : dict, optional
            The query parameters for the request.
        errors : dict, optional
            A dictionary mapping status codes to exception handlers.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.get(self.path, params=params, errors=errors)

    def post(self, data: dict) -> dict:
        """Create a new item in the collection.

        Parameters
        ----------
        data : dict
            The data to send in the request body.

        Returns
        -------
        dict
            The JSON response from the API.
        """
        return self.rest.post(self.path, data, errors={409: AlreadyExists})

    def __repr__(self) -> str:
        """Return a string representation of the RestItemList."""
        return f"{self.__class__.__name__}({self.collection})"
