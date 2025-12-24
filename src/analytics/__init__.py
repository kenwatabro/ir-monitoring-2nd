"""Analytics module for screening and filtering stocks."""

from .registry import auto_discover, get_screener, list_screeners, register

__all__ = [
    "auto_discover",
    "get_screener",
    "list_screeners",
    "register",
]
