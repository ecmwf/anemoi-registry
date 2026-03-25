# (C) Copyright 2026 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

"""Unit tests for :mod:`anemoi.registry.v*.rest` — HTTP mocked, no server."""

import datetime
import math

import pytest
import responses

from anemoi.registry.v1.rest import AlreadyExists, Rest

# ---------------------------------------------------------------------------
# Rest — HTTP methods (mocked with `responses`)
# ---------------------------------------------------------------------------

API_URL = "https://anemoi-test.ecmwf.int/api/v1"


@pytest.fixture
def mock_rest(monkeypatch):
    """Return a ``Rest`` instance with a patched ``api_url`` and ``config``."""
    class FakeConfig:
        api_url = API_URL
        api_token = "test-token-123"
        def get(self, key, default=None):
            if key == "allow_delete":
                return True
            return default

    monkeypatch.setattr(Rest, "config", property(lambda self: FakeConfig()))
    return Rest(token="test-token-123")


class TestRestGet:
    @responses.activate
    def test_get_success(self, mock_rest):
        responses.add(
            responses.GET, f"{API_URL}/datasets/my-ds",
            json={"name": "my-ds"}, status=200,
        )
        result = mock_rest.get("datasets/my-ds")
        assert result == {"name": "my-ds"}

    @responses.activate
    def test_get_with_params(self, mock_rest):
        responses.add(responses.GET, f"{API_URL}/datasets", json=[], status=200)
        mock_rest.get("datasets", params={"limit": "5"})
        assert "limit=5" in responses.calls[0].request.url

    @responses.activate
    def test_get_404_raises(self, mock_rest):
        responses.add(responses.GET, f"{API_URL}/datasets/nope", status=404, body="not found")
        from requests.exceptions import HTTPError
        with pytest.raises(HTTPError):
            mock_rest.get("datasets/nope")


class TestRestPost:
    @responses.activate
    def test_post_success(self, mock_rest):
        responses.add(
            responses.POST, f"{API_URL}/datasets",
            json={"name": "new-ds"}, status=201,
        )
        result = mock_rest.post("datasets", {"name": "new-ds"})
        assert result == {"name": "new-ds"}

    @responses.activate
    def test_post_409_with_error_handler(self, mock_rest):
        responses.add(responses.POST, f"{API_URL}/datasets", status=409, body="duplicate")
        with pytest.raises(AlreadyExists):
            mock_rest.post("datasets", {"name": "dup"}, errors={409: AlreadyExists})


class TestRestPut:
    @responses.activate
    def test_put_success(self, mock_rest):
        responses.add(
            responses.PUT, f"{API_URL}/datasets/ds1",
            json={"name": "ds1", "status": "updated"}, status=200,
        )
        result = mock_rest.put("datasets/ds1", {"name": "ds1", "status": "updated"})
        assert result["status"] == "updated"

    def test_put_empty_data_raises(self, mock_rest):
        with pytest.raises(ValueError, match="PUT data must be provided"):
            mock_rest.put("datasets/ds1", {})


class TestRestPatch:
    @responses.activate
    def test_patch_success(self, mock_rest):
        responses.add(
            responses.PATCH, f"{API_URL}/datasets/ds1",
            json={"ok": True}, status=200,
        )
        result = mock_rest.patch(
            "datasets/ds1",
            [{"op": "add", "path": "/metadata/status", "value": "testing"}],
        )
        assert result == {"ok": True}

    def test_patch_empty_data_raises(self, mock_rest):
        with pytest.raises(ValueError, match="PATCH data must be provided"):
            mock_rest.patch("datasets/ds1", [])


class TestRestDelete:
    @responses.activate
    def test_delete_success(self, mock_rest):
        responses.add(
            responses.DELETE, f"{API_URL}/datasets/ds1",
            json={"deleted": True}, status=200,
        )
        result = mock_rest.delete("datasets/ds1")
        assert result == {"deleted": True}

    def test_delete_not_allowed(self, monkeypatch):
        """If allow_delete is False, delete raises before hitting the network."""
        class FakeConfig:
            api_url = API_URL
            api_token = "test-token-123"
            def get(self, key, default=None):
                if key == "allow_delete":
                    return False
                return default

        monkeypatch.setattr(Rest, "config", property(lambda self: FakeConfig()))
        r = Rest(token="test-token-123")
        with pytest.raises(ValueError, match="not allowed"):
            r.delete("datasets/ds1")


class TestRestExists:
    @responses.activate
    def test_exists_true(self, mock_rest):
        responses.add(responses.GET, f"{API_URL}/datasets/ds1", json={}, status=200)
        assert mock_rest.exists("datasets/ds1") is True

    @responses.activate
    def test_exists_false(self, mock_rest):
        responses.add(responses.GET, f"{API_URL}/datasets/nope", status=404, body="not found")
        assert mock_rest.exists("datasets/nope") is False