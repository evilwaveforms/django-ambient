from __future__ import annotations

from typing import Any

_cache_calls: dict[int, list[tuple[str, str, Any, int | None, int | None, float]]] = {}


def store_cache_calls(
    request_id: int,
    calls: list[tuple[str, str, Any, int | None, int | None, float]],
) -> None:
    _cache_calls[request_id] = list(calls)


def get_cache_calls(
    request_id: int,
) -> list[tuple[str, str, Any, int | None, int | None, float]]:
    return list(_cache_calls.get(request_id, ()))


def evict_cache_calls(request_id: int) -> None:
    _cache_calls.pop(request_id, None)

