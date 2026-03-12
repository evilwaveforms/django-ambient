import time
from django.db import connection
from django_ambient._core import start_profile, record_queries
from django_ambient.sql import store_sql_params, evict_sql_params
from django_ambient.stack import capture_stack_frames, store_stack_trace, evict_stack_traces


def ambient_middleware(get_response):
    def middleware(request):
        request_id = start_profile()
        started_at = time.time()
        collected_queries: list[tuple[str, int, float]] = []

        def wrapper(execute, sql, params, many, context_):
            t0 = time.perf_counter()
            try:
                return execute(sql, params, many, context_)
            finally:
                dt_ms = (time.perf_counter() - t0) * 1000.0

                frames = capture_stack_frames(skip=1, max_frames=30)
                store_stack_trace(request_id, frames)
                store_sql_params(request_id, params, many)
                collected_queries.append((sql, 0, dt_ms))

        with connection.execute_wrapper(wrapper):
            response = get_response(request)

        if collected_queries:
            evicted = record_queries(
                request_id,
                request.path,
                request.method,
                response.status_code,
                collected_queries,
                started_at,
            )
            if evicted:
                evict_sql_params(evicted)
                evict_stack_traces(evicted)
        return response
    return middleware
