import json
import time

from django.http import Http404, StreamingHttpResponse
from django.shortcuts import render

from django_ambient import _core
from django_ambient.stack import get_stack_trace, render_stack_trace, get_stack_traces


def index(request):
    requests = _format_requests(_core.list_requests())
    max_requests = _core.max_requests()
    return render(
        request,
        "django_ambient/index.html",
        {
            "requests": requests,
            "max_requests": max_requests,
        },
    )


def request_detail(request, request_id: int):
    data = _core.get_request(request_id)
    if data is None:
        raise Http404("Request not found")
    path, method, status, queries, started_at = data
    trace_count = len(get_stack_traces(request_id))
    queries_with_traces = []
    for idx, (sql, duplicates, duration_ms) in enumerate(queries):
        queries_with_traces.append(
            {
                "sql": sql,
                "duplicates": duplicates,
                "duration_ms": duration_ms,
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
            "started_at": _format_timestamp(started_at),
        },
    )

def query_stack_trace(request, request_id: int, query_index: int):
    data = _core.get_request(request_id)
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


def _serialize_requests(
    items: list[tuple[int, str, str, int, int, float, str]],
) -> list[dict[str, object]]:
    return [
        {
            "id": req_id,
            "path": path,
            "method": method,
            "status": status,
            "query_count": query_count,
            "total_ms": total_ms,
            "started_at": started_at,
        }
        for req_id, path, method, status, query_count, total_ms, started_at in items
    ]


def events(request):
    def event_stream():
        last_ids: set[int] | None = None
        while True:
            requests = _format_requests(_core.list_requests())
            current_ids = {req_id for req_id, *_ in requests}

            if last_ids is None:
                payload = json.dumps(_serialize_requests(requests))
                yield f"event: snapshot\ndata: {payload}\n\n"
                last_ids = current_ids
                time.sleep(1)
                continue
            if current_ids == last_ids:
                time.sleep(1)
                continue

            added_ids = current_ids - last_ids
            removed_ids = last_ids - current_ids
            if added_ids:
                new_requests = [req for req in requests if req[0] in added_ids]
                payload = json.dumps(_serialize_requests(new_requests))
                yield f"event: append\ndata: {payload}\n\n"
            if removed_ids:
                payload = json.dumps(sorted(removed_ids))
                yield f"event: remove\ndata: {payload}\n\n"
            last_ids = current_ids
            time.sleep(1)
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


def _format_timestamp(value: float) -> str:
    ts = time.localtime(value)
    return time.strftime("%H:%M:%S", ts)


def _format_requests(
    items: list[tuple[int, str, str, int, int, float, float]],
) -> list[tuple[int, str, str, int, int, float, str]]:
    return [
        (
            req_id,
            path,
            method,
            status,
            query_count,
            total_ms,
            _format_timestamp(started_at),
        )
        for req_id, path, method, status, query_count, total_ms, started_at in items
    ]
