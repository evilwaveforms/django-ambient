import time


def format_timestamp(value: float) -> str:
    ts = time.localtime(value)
    return time.strftime("%H:%M:%S", ts)


def serialize_requests(items: list[tuple]) -> list[dict[str, object]]:
    return [
        {
            "id": req_id,
            "path": path,
            "method": method,
            "status": status,
            "query_count": query_count,
            "total_ms": total_ms,
            "started_at": format_timestamp(started_at),
            "duration_ms": duration_ms,
            "cpu_ms": cpu_ms,
            "template_ms": template_ms,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_ms": cache_ms,
        }
        for (
            req_id,
            path,
            method,
            status,
            query_count,
            total_ms,
            started_at,
            duration_ms,
            cpu_ms,
            template_ms,
            (cache_hits, cache_misses, cache_ms),
        ) in items
    ]


def format_requests(
    items: list[tuple],
) -> list[tuple[int, str, str, int, int, float, str, float, float, float, int, int, float]]:
    return [
        (
            req_id,
            path,
            method,
            status,
            query_count,
            total_ms,
            format_timestamp(started_at),
            duration_ms,
            cpu_ms,
            template_ms,
            cache_hits,
            cache_misses,
            cache_ms,
        )
        for (
            req_id,
            path,
            method,
            status,
            query_count,
            total_ms,
            started_at,
            duration_ms,
            cpu_ms,
            template_ms,
            (cache_hits, cache_misses, cache_ms),
        ) in items
    ]


def format_cache_calls(
    calls: list[tuple[str, str, object, int | None, int | None, float, list[tuple[str, int, str]]]],
) -> list[dict[str, object]]:
    formatted = []
    for index, (op, backend, key, hits, misses, duration_ms, frames) in enumerate(calls):
        formatted.append(
            {
                "index": index,
                "op": op,
                "backend": backend,
                "key": format_cache_key(key),
                "hits": hits,
                "misses": misses,
                "duration_ms": duration_ms,
                "has_trace": bool(frames),
            }
        )
    return formatted


def format_cache_key(value: object) -> str:
    if isinstance(value, (list, tuple)):
        parts = [str(item) for item in value[:5]]
        if len(value) > 5:
            parts.append("...")
        return ", ".join(parts)
    return str(value)
