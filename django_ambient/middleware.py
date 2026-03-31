from contextlib import ExitStack
import time
from django.db import connections
from django.urls import NoReverseMatch, reverse
from django_ambient._store import start_profile, record_queries
from django_ambient.cache_calls import evict_cache_calls, store_cache_calls
from django_ambient.metrics import install_hooks, start_request_metrics, end_request_metrics
from django_ambient.sql import store_sql_params, evict_sql_params
from django_ambient.stack import capture_stack_frames, store_stack_trace, evict_stack_traces

_ambient_prefix: str | None = None
_cpu_clock = time.thread_time if hasattr(time, "thread_time") else time.process_time
_hooks_installed = False


def _is_ambient_request(request) -> bool:
    global _ambient_prefix
    if _ambient_prefix is None:
        try:
            prefix = reverse("ambient-index")
        except NoReverseMatch:
            _ambient_prefix = ""
        else:
            _ambient_prefix = prefix if prefix.endswith("/") else f"{prefix}/"
    if not _ambient_prefix:
        return False
    path = request.path
    return path == _ambient_prefix.rstrip("/") or path.startswith(_ambient_prefix)


def ambient_middleware(get_response):
    def middleware(request):
        global _hooks_installed
        if _is_ambient_request(request):
            return get_response(request)

        if not _hooks_installed:
            install_hooks()
            _hooks_installed = True

        request_id = start_profile()
        started_at = time.time()
        wall_start = time.perf_counter()
        cpu_start = _cpu_clock()
        metric_tokens = start_request_metrics()
        collected_queries: list[tuple[str, int, float]] = []

        def wrapper(execute, sql, params, many, context_):
            t0 = time.perf_counter()
            try:
                return execute(sql, params, many, context_)
            finally:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                connection_obj = context_.get("connection")
                using = getattr(connection_obj, "alias", "default")

                frames = capture_stack_frames(skip=1, max_frames=30)
                store_stack_trace(request_id, frames)
                store_sql_params(request_id, using, params, many)
                collected_queries.append((sql, 0, dt_ms))

        with ExitStack() as stack:
            for conn in connections.all():
                stack.enter_context(conn.execute_wrapper(wrapper))
            response = get_response(request)

        duration_ms = (time.perf_counter() - wall_start) * 1000.0
        cpu_ms = (_cpu_clock() - cpu_start) * 1000.0
        cache_stats, cache_calls, template_stats = end_request_metrics(metric_tokens)
        store_cache_calls(request_id, cache_calls)

        evicted = record_queries(
            request_id,
            request.path,
            request.method,
            response.status_code,
            collected_queries,
            started_at,
            duration_ms,
            cpu_ms,
            template_stats["time_ms"],
            cache_stats["hits"],
            cache_stats["misses"],
            cache_stats["time_ms"],
        )
        if evicted:
            evict_sql_params(evicted)
            evict_stack_traces(evicted)
            evict_cache_calls(evicted)
        return response

    return middleware
