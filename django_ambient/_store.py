from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
from itertools import count
from threading import Lock

MAX_REQUESTS = 100


@dataclass(slots=True)
class RequestData:
    id: int
    path: str
    method: str
    status: int
    queries: list[tuple[str, int, float]]
    started_at: float
    duration_ms: float
    cpu_ms: float
    template_ms: float
    cache_hits: int
    cache_misses: int
    cache_ms: float


_next_id = count(1)
_lock = Lock()
_requests: OrderedDict[int, RequestData] = OrderedDict()
_evicted_ids: deque[int] = deque()


def start_profile() -> int:
    return next(_next_id)


def record_queries(
    request_id: int,
    path: str,
    method: str,
    status: int,
    queries: list[tuple[str, int, float]],
    started_at: float,
    duration_ms: float,
    cpu_ms: float,
    template_ms: float,
    cache_hits: int,
    cache_misses: int,
    cache_ms: float,
) -> int | None:
    request = RequestData(
        id=request_id,
        path=path,
        method=method,
        status=status,
        queries=list(queries),
        started_at=started_at,
        duration_ms=duration_ms,
        cpu_ms=cpu_ms,
        template_ms=template_ms,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        cache_ms=cache_ms,
    )
    with _lock:
        evicted_id = None
        if MAX_REQUESTS > 0 and len(_requests) >= MAX_REQUESTS:
            evicted_id, _ = _requests.popitem(last=False)
            _evicted_ids.append(evicted_id)
        if MAX_REQUESTS > 0:
            _requests[request_id] = request
    return evicted_id


def get_request(
    request_id: int,
) -> tuple[str, str, int, list[tuple[str, int, float]], float, float, float, float, tuple[int, int, float]] | None:
    with _lock:
        request = _requests.get(request_id)
        if request is None:
            return None
        return (
            request.path,
            request.method,
            request.status,
            _annotate_duplicates(request.queries),
            request.started_at,
            request.duration_ms,
            request.cpu_ms,
            request.template_ms,
            (request.cache_hits, request.cache_misses, request.cache_ms),
        )


def list_requests(
) -> list[tuple[int, str, str, int, int, float, float, float, float, float, tuple[int, int, float]]]:
    with _lock:
        return [_serialize_request(request) for request in reversed(tuple(_requests.values()))]


def list_requests_since(
    last_id: int,
) -> list[tuple[int, str, str, int, int, float, float, float, float, float, tuple[int, int, float]]]:
    items: list[tuple[int, str, str, int, int, float, float, float, float, float, tuple[int, int, float]]] = []
    with _lock:
        for request in reversed(tuple(_requests.values())):
            if request.id <= last_id:
                break
            items.append(_serialize_request(request))
    return items


def drain_evicted_ids() -> list[int]:
    with _lock:
        items = list(_evicted_ids)
        _evicted_ids.clear()
        return items


def max_requests() -> int:
    return MAX_REQUESTS


def _annotate_duplicates(data: list[tuple[str, int, float]]) -> list[tuple[str, int, float]]:
    counts: dict[str, int] = {}
    for query, _, _ in data:
        counts[query] = counts.get(query, 0) + 1
    return [(query, counts.get(query, 0), duration_ms) for query, _, duration_ms in data]


def _serialize_request(
    request: RequestData,
) -> tuple[int, str, str, int, int, float, float, float, float, float, tuple[int, int, float]]:
    total_ms = sum(query[2] for query in request.queries)
    return (
        request.id,
        request.path,
        request.method,
        request.status,
        len(request.queries),
        total_ms,
        request.started_at,
        request.duration_ms,
        request.cpu_ms,
        request.template_ms,
        (request.cache_hits, request.cache_misses, request.cache_ms),
    )

