from __future__ import annotations

from contextvars import ContextVar


_API_CREDENTIALS: ContextVar[dict[str, str]] = ContextVar("_API_CREDENTIALS", default={})


def set_api_credentials(**credentials: str | None) -> None:
    sanitized = {key: value for key, value in credentials.items() if value}
    _API_CREDENTIALS.set(sanitized)


def clear_api_credentials() -> None:
    _API_CREDENTIALS.set({})


def get_api_credential(*keys: str, default: str | None = None) -> str | None:
    current = _API_CREDENTIALS.get()
    for key in keys:
        value = current.get(key)
        if value:
            return value
    return default


def current_api_credentials() -> dict[str, str]:
    return dict(_API_CREDENTIALS.get())
