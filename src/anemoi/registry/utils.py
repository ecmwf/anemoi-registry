# (C) Copyright 2024 European Centre for Medium-Range Weather Forecasts.
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.


def list_to_dict(lst):
    assert isinstance(lst, (tuple, list)), f"lst must be a list. Got {lst} of type {type(lst)}."
    for x in lst:
        assert isinstance(x, str), f"lst must be a list of strings. Got {x} of type {type(x)}."
        if "=" not in x:
            raise ValueError(f"Invalid key-value pairs format '{x}', use 'key1=value1 key2=value2' list.")
    return {x.split("=")[0]: x.split("=")[1] for x in lst}
