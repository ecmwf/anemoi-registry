# Tests

All tests run against the **test catalogue** (`ANEMOI_CATALOGUE=TEST`), never production. This is enforced by an `autouse` fixture in `conftest.py`.

## Test layers

| Directory       | What it tests                              | Requirements                          |
|-----------------|--------------------------------------------|---------------------------------------|
| `unit/`         | Configuration, entry paths, REST client    | HTTP-mocked, no server needed         |
| `integration/`  | Python API against the live test catalogue | Test catalogue token                  |
| `cli/`          | Subprocess invocations of `anemoi-registry`| Test catalogue token                  |

**unit** tests can run anywhere (including CI without credentials).
**integration** and **cli** tests are skipped in GitHub Actions where no catalogue token is available.

## CLI versioning

Most CLI tests are parametrised over both v1 and v2 (`ANEMOI_REGISTRY_CLI_VERSION=1|2`). Fixtures `cli_version`, `v1_only`, and `v2_only` handle the environment setup and module reloading.

## Running

```bash
# Full suite (needs test catalogue credentials)
ANEMOI_CATALOGUE=TEST python -m pytest tests/

# Skip tests that need the `responses` library
ANEMOI_CATALOGUE=TEST python -m pytest tests/ --ignore=tests/unit/test_rest_client.py
```
