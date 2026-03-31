from __future__ import annotations

from collections import OrderedDict
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


_next_id = count(1)
_lock = Lock()
_requests: OrderedDict[int, RequestData] = OrderedDict()


def start_profile() -> int:
    return next(_next_id)


def record_queries(
    request_id: int,
    path: str,
    method: str,
    status: int,
    queries: list[tuple[str, int, float]],
    started_at: float,
) -> int | None:
    request = RequestData(
        id=request_id,
        path=path,
        method=method,
        status=status,
        queries=list(queries),
        started_at=started_at,
    )
    with _lock:
        evicted_id = None
        if MAX_REQUESTS > 0 and len(_requests) >= MAX_REQUESTS:
            evicted_id, _ = _requests.popitem(last=False)
        if MAX_REQUESTS > 0:
            _requests[request_id] = request
    return evicted_id


def get_request(
    request_id: int,
) -> tuple[str, str, int, list[tuple[str, int, float]], float] | None:
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
        )


def list_requests() -> list[tuple[int, str, str, int, int, float, float]]:
    with _lock:
        return [_serialize_request(request) for request in reversed(tuple(_requests.values()))]


def max_requests() -> int:
    return MAX_REQUESTS


def _annotate_duplicates(data: list[tuple[str, int, float]]) -> list[tuple[str, int, float]]:
    counts: dict[str, int] = {}
    for query, _, _ in data:
        counts[query] = counts.get(query, 0) + 1
    return [(query, counts.get(query, 0), duration_ms) for query, _, duration_ms in data]


def _serialize_request(request: RequestData) -> tuple[int, str, str, int, int, float, float]:
    total_ms = sum(query[2] for query in request.queries)
    return (
        request.id,
        request.path,
        request.method,
        request.status,
        len(request.queries),
        total_ms,
        request.started_at,
    )
