from django.urls import path

from django_ambient import views

urlpatterns = [
    path("", views.index, name="ambient-index"),
    path("events/", views.events, name="ambient-events"),
    path("requests/<int:request_id>/", views.request_detail, name="ambient-request-detail"),
    path(
        "requests/<int:request_id>/queries/<int:query_index>/stack/",
        views.query_stack_trace,
        name="ambient-query-stack",
    ),
    path(
        "requests/<int:request_id>/cache/<int:call_index>/stack/",
        views.cache_call_stack_trace,
        name="ambient-cache-stack",
    ),
]
