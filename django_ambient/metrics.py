import contextvars
import time

_cache_stats_var = contextvars.ContextVar("ambient_cache_stats", default=None)
_cache_calls_var = contextvars.ContextVar("ambient_cache_calls", default=None)
_cache_depth = contextvars.ContextVar("ambient_cache_depth", default=0)
_template_stats_var = contextvars.ContextVar("ambient_template_stats", default=None)
_template_depth = contextvars.ContextVar("ambient_template_depth", default=0)

_CACHE_PATCHED = False
_TEMPLATE_PATCHED = False
_MISSING = object()


def install_hooks() -> None:
    install_cache_hooks()
    install_template_hooks()


def start_request_metrics():
    cache_token = _cache_stats_var.set({"hits": 0, "misses": 0, "time_ms": 0.0})
    cache_calls_token = _cache_calls_var.set([])
    template_token = _template_stats_var.set({"time_ms": 0.0})
    cache_depth_token = _cache_depth.set(0)
    template_depth_token = _template_depth.set(0)
    return cache_token, cache_calls_token, template_token, cache_depth_token, template_depth_token


def end_request_metrics(tokens):
    cache_stats = _cache_stats_var.get() or {"hits": 0, "misses": 0, "time_ms": 0.0}
    cache_calls = _cache_calls_var.get() or []
    template_stats = _template_stats_var.get() or {"time_ms": 0.0}
    cache_token, cache_calls_token, template_token, cache_depth_token, template_depth_token = tokens
    _cache_stats_var.reset(cache_token)
    _cache_calls_var.reset(cache_calls_token)
    _template_stats_var.reset(template_token)
    _cache_depth.reset(cache_depth_token)
    _template_depth.reset(template_depth_token)
    return cache_stats, cache_calls, template_stats


def install_cache_hooks() -> None:
    global _CACHE_PATCHED
    if _CACHE_PATCHED:
        return

    from django.core.cache.backends.base import BaseCache

    if getattr(BaseCache, "_ambient_cache_wrapped", False):
        _CACHE_PATCHED = True
        return

    orig_get = BaseCache.get
    orig_get_many = BaseCache.get_many
    orig_set = BaseCache.set
    orig_set_many = BaseCache.set_many
    orig_add = BaseCache.add
    orig_delete = BaseCache.delete
    orig_clear = BaseCache.clear

    def _record(stats, calls, depth, start, op, backend, key, hits, misses):
        if start is None or depth != 0:
            return
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if stats is not None:
            stats["time_ms"] += elapsed_ms
            if hits:
                stats["hits"] += hits
            if misses:
                stats["misses"] += misses
        if calls is not None:
            calls.append((op, backend, key, hits, misses, elapsed_ms))

    def get(self, key, default=None, version=None):
        stats = _cache_stats_var.get()
        calls = _cache_calls_var.get()
        depth = _cache_depth.get()
        _cache_depth.set(depth + 1)
        start = time.perf_counter() if depth == 0 else None
        hit = False
        backend = f"{self.__class__.__module__}.{self.__class__.__name__}"
        try:
            value = orig_get(self, key, _MISSING, version=version)
            hit = value is not _MISSING
            if not hit:
                value = default
            return value
        finally:
            _record(
                stats,
                calls,
                depth,
                start,
                "get",
                backend,
                key,
                1 if hit else 0,
                0 if hit else 1,
            )
            _cache_depth.set(depth)

    def get_many(self, keys, version=None):
        stats = _cache_stats_var.get()
        calls = _cache_calls_var.get()
        depth = _cache_depth.get()
        _cache_depth.set(depth + 1)
        keys_list = list(keys)
        start = time.perf_counter() if depth == 0 else None
        backend = f"{self.__class__.__module__}.{self.__class__.__name__}"
        result = {}
        try:
            result = orig_get_many(self, keys_list, version=version)
            return result
        finally:
            hits = len(result) if "result" in locals() else 0
            misses = len(keys_list) - hits
            _record(stats, calls, depth, start, "get_many", backend, keys_list, hits, misses)
            _cache_depth.set(depth)

    def _wrap_nohit(orig):
        def wrapper(self, *args, **kwargs):
            stats = _cache_stats_var.get()
            calls = _cache_calls_var.get()
            depth = _cache_depth.get()
            _cache_depth.set(depth + 1)
            start = time.perf_counter() if depth == 0 else None
            backend = f"{self.__class__.__module__}.{self.__class__.__name__}"
            try:
                return orig(self, *args, **kwargs)
            finally:
                key = args[0] if args else None
                _record(stats, calls, depth, start, orig.__name__, backend, key, None, None)
                _cache_depth.set(depth)
        return wrapper

    BaseCache.get = get
    BaseCache.get_many = get_many
    BaseCache.set = _wrap_nohit(orig_set)
    BaseCache.set_many = _wrap_nohit(orig_set_many)
    BaseCache.add = _wrap_nohit(orig_add)
    BaseCache.delete = _wrap_nohit(orig_delete)
    BaseCache.clear = _wrap_nohit(orig_clear)
    BaseCache._ambient_cache_wrapped = True
    _CACHE_PATCHED = True


def install_template_hooks() -> None:
    global _TEMPLATE_PATCHED
    if _TEMPLATE_PATCHED:
        return

    from django.template.base import Template

    if getattr(Template, "_ambient_template_wrapped", False):
        _TEMPLATE_PATCHED = True
        return

    orig_render = Template.render

    def render(self, context):
        stats = _template_stats_var.get()
        depth = _template_depth.get()
        _template_depth.set(depth + 1)
        start = time.perf_counter() if stats is not None and depth == 0 else None
        try:
            return orig_render(self, context)
        finally:
            if stats is not None and depth == 0 and start is not None:
                stats["time_ms"] += (time.perf_counter() - start) * 1000.0
            _template_depth.set(depth)

    Template.render = render
    Template._ambient_template_wrapped = True
    _TEMPLATE_PATCHED = True
