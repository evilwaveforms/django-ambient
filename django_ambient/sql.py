from django.db import connections
from typing import Any

_sql_params: dict[int, list[tuple[str, Any, bool]]] = {}

def store_sql_params(request_id: int, using: str, params: Any, many: bool) -> None:
    items = _sql_params.setdefault(request_id, [])
    items.append((using, params, many))

def evict_sql_params(request_id: int) -> None:
    _sql_params.pop(request_id, None)

def _normalize_rows(params: Any, many: bool) -> list[list[object]]:
    if many:
        rows: list[list[object]] = []
        for row_params in params or ():
            if row_params is None:
                norm_row: list[object] = []
            elif isinstance(row_params, (list, tuple)):
                norm_row = list(row_params)
            else:
                norm_row = [row_params]
            rows.append(norm_row)
        return rows
    else:
        if params is None:
            norm_row: list[object] = []
        elif isinstance(params, (list, tuple)):
            norm_row = list(params)
        else:
            norm_row = [params]
        return [norm_row]

def _render_sql(sql: str, row_params: list[object], using: str = "default") -> str:
    conn = connections[using]
    cursor = conn.cursor()
    try:
        if hasattr(cursor, "mogrify"):
            return cursor.mogrify(sql, row_params or ()).decode()
        return conn.ops.last_executed_query(cursor, sql, row_params or ())
    finally:
        cursor.close()

def format_sql_for_request(request_id: int, sql_list: list[str]) -> list[str]:
    items = list(_sql_params.get(request_id, ()))
    result: list[str] = []

    for sql, (using, params, many) in zip(sql_list, items):
        rows = _normalize_rows(params, many)
        first_row = rows[0] if rows else []
        full_sql = _render_sql(sql, first_row, using=using)
        result.append(full_sql)
    return result
