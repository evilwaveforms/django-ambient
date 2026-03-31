import inspect
import sys
import linecache
import os

EXCLUDED_MODULE_PREFIXES = (
    "django.db",
    "django_ambient",
)

_stack_traces: dict[int, list[list[tuple[str, int, str]]]] = {}

def store_stack_trace(request_id: int, frames: list[tuple[str, int, str]]) -> None:
    items = _stack_traces.setdefault(request_id, [])
    items.append(frames)

def evict_stack_traces(request_id: int) -> None:
    _stack_traces.pop(request_id, None)

def capture_stack_frames(skip: int = 0, max_frames: int | None = None):
  try:
      frame = sys._getframe(skip + 1)
  except (AttributeError, ValueError):
      return []

  result = []
  depth = 0
  while frame and (max_frames is None or depth < max_frames):
      code = frame.f_code
      result.append((code.co_filename, frame.f_lineno, code.co_name))
      frame = frame.f_back
      depth += 1
  return result

def get_stack_traces(request_id: int) -> list[list[tuple[str, int, str]]]:
    return list(_stack_traces.get(request_id, ()))

def render_stack_traces(request_id: int, max_frames: int = 5) -> list[list[dict[str, object]]]:
    traces = get_stack_traces(request_id)
    return [render_stack_trace(trace, max_frames=max_frames) for trace in traces]

def get_stack_trace(
    request_id: int,
    index: int,
) -> list[tuple[str, int, str]] | None:
    traces = _stack_traces.get(request_id)
    if traces is None:
        return None
    if index < 0 or index >= len(traces):
        return None
    return traces[index]

def render_stack_trace(
    frames: list[tuple[str, int, str]],
    max_frames: int = 5,
) -> list[dict[str, object]]:
    selected = _select_relevant_frames(frames, max_frames=max_frames)
    rendered: list[dict[str, object]] = []
    for filename, lineno, func in selected:
        line = linecache.getline(filename, lineno).rstrip("\n")
        rendered.append(
            {
                "filename": filename,
                "lineno": lineno,
                "func": func,
                "line": line,
            }
        )
    return rendered

def _select_relevant_frames(
    frames: list[tuple[str, int, str]],
    max_frames: int,
) -> list[tuple[str, int, str]]:
    if not frames:
        return []
    start = 0
    for idx, (filename, _, _) in enumerate(frames):
        if _is_user_frame(filename):
            start = idx
            break
    return frames[start:start + max_frames]

def _is_user_frame(file_name: str) -> bool:
    file_name = file_name.replace("\\", "/")
    if "/site-packages/" in file_name:
        return False
    for prefix in EXCLUDED_MODULE_PREFIXES:
        if f"/{prefix.replace('.', '/')}/" in file_name:
            return False
    if "/lib/python" in file_name:
        return False
    return os.path.isabs(file_name)
