# django-ambient


## Install

For local development of this package:

```bash
uv sync
uv pip install -e .
```

To use it from another Django app with `uv`:

```bash
uv add --editable /path/to/django-ambient
```

Or with `pip`:

```bash
pip install -e /path/to/django-ambient
```

## Django setup

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_ambient",
]
```

Add the middleware to `MIDDLEWARE`:

```python
MIDDLEWARE = [
    # ...
    "django_ambient.middleware.ambient_middleware",
]
```

Add the middleware URLs somewhere in your project, for example under `/ambient/`:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("ambient/", include("django_ambient.urls")),
]
```
