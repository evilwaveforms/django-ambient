import json
import time

from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render

from django_ambient import _store
from django_ambient.cache_calls import get_cache_calls
from django_ambient.stack import get_stack_trace, render_stack_trace, get_stack_traces
from django_ambient.utils import (
    format_cache_calls,
    format_requests,
    format_timestamp,
    serialize_requests,
)


def index(request):
    requests = format_requests(_store.list_requests())
    max_requests = _store.max_requests()
    last_request_id = requests[0][0] if requests else 0
    return render(
        request,
        "django_ambient/index.html",
        {
            "requests": requests,
            "max_requests": max_requests,
            "last_request_id": last_request_id,
        },
    )

def request_detail(request, request_id: int):
    data = _store.get_request(request_id)
    if data is None:
        raise Http404("Request not found")
    (
        path,
        method,
        status,
        queries,
        started_at,
        duration_ms,
        cpu_ms,
        template_ms,
        cache_stats,
    ) = data
    cache_hits, cache_misses, cache_ms = cache_stats
    cache_calls = format_cache_calls(get_cache_calls(request_id))
    trace_count = len(get_stack_traces(request_id))
    queries_with_traces = []
    for idx, (sql, duplicates, query_duration_ms) in enumerate(queries):
        queries_with_traces.append(
            {
                "sql": sql,
                "duplicates": duplicates,
                "duration_ms": query_duration_ms,
                "index": idx,
                "has_trace": idx < trace_count,
            }
        )
    return render(
        request,
        "django_ambient/request_detail.html",
        {
            "request_id": request_id,
            "path": path,
            "method": method,
            "status": status,
            "queries": queries_with_traces,
            "started_at": format_timestamp(started_at),
            "duration_ms": duration_ms,
            "cpu_ms": cpu_ms,
            "template_ms": template_ms,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_ms": cache_ms,
            "cache_calls": cache_calls,
        },
    )


def query_stack_trace(request, request_id: int, query_index: int):
    data = _store.get_request(request_id)
    if not data:
        raise Http404("Request not found")
    trace = get_stack_trace(request_id, query_index)
    if not trace:
        raise Http404("Stack trace not found")
    frames = render_stack_trace(trace)
    return render(
        request,
        "django_ambient/stack_trace.html",
        {"frames": frames},
    )


def cache_call_stack_trace(request, request_id: int, call_index: int):
    data = _store.get_request(request_id)
    if not data:
        raise Http404("Request not found")
    cache_calls = get_cache_calls(request_id)
    if call_index < 0 or call_index >= len(cache_calls):
        raise Http404("Cache call not found")
    frames = cache_calls[call_index][6]
    if not frames:
        raise Http404("Stack trace not found")
    rendered = render_stack_trace(frames)
    return render(
        request,
        "django_ambient/stack_trace.html",
        {"frames": rendered},
    )


def events(request):
    def event_stream():
        since = request.GET.get("since")
        try:
            last_id = int(since) if since is not None else 0
        except ValueError:
            last_id = 0

        while True:
            new_requests = _store.list_requests_since(last_id)
            if new_requests:
                payload = json.dumps(serialize_requests(new_requests))
                yield f"event: append\ndata: {payload}\n\n"
                last_id = new_requests[0][0]

            evicted_ids = _store.drain_evicted_ids()
            if evicted_ids:
                payload = json.dumps(evicted_ids)
                yield f"event: remove\ndata: {payload}\n\n"

            time.sleep(1)

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
