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
