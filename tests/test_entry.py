# (C) Copyright 2024 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


from anemoi.registry.entry import CatalogueEntry


def test_resolve_path():
    for x, y in [
        ("updated", "/metadata/updated"),
        ("a.b", "/metadata/a/b"),
        ("/top/value", "/top/value"),
        (".top.value", "/top/value"),
        (".metadata.updated", "/metadata/updated"),
        ("/metadata/key.with.dot", "/metadata/key.with.dot"),
    ]:
        actual = CatalogueEntry.resolve_path(x, check=False)
        assert actual == y, "%s -> %s, expected: %s" % (x, actual, y)
        actual = CatalogueEntry.resolve_path(actual, check=False)
        assert actual == y, "%s -> %s, expected: %s" % (actual, actual, y)
