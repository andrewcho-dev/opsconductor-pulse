# Task 1: Add `require_env()` Helper to Shared Utilities

## Context

All microservices need a consistent way to read required environment variables and fail fast with a clear error message if one is missing. Rather than duplicating this logic in every service, add it once to `services/shared/`.

## Actions

1. Open `services/shared/config.py`. If the file does not exist, create it.

2. Add the following utility function:

```python
import os

def require_env(name: str) -> str:
    """
    Read a required environment variable.
    Raises RuntimeError at startup if the variable is absent or empty.
    Use this for all security-sensitive configuration (passwords, secrets, keys).
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            "Set it before starting the service."
        )
    return value


def optional_env(name: str, default: str = "") -> str:
    """
    Read an optional environment variable with a safe default.
    Use this only for non-sensitive config (ports, log levels, feature flags).
    """
    return os.environ.get(name, default)
```

3. If `services/shared/__init__.py` exports anything, add `require_env` and `optional_env` to the exports. If it is empty, leave it as-is (callers will import directly from `shared.config`).

4. Do not modify any other files in this task.

## Verification

- `services/shared/config.py` exists and contains both functions.
- `require_env("")` raises `RuntimeError`.
- `require_env("PATH")` returns a non-empty string (PATH is always set).
