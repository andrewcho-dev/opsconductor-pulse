"""
Structured logging context helpers.

This module intentionally keeps a tiny surface area so services can share
`trace_id` context without changing their logger callsites.
"""

from contextvars import ContextVar
import logging

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
