try:
    from functools import cached_property
except ImportError:
    from django.utils.functional import cached_property  # type: ignore  # noqa: F401

__all__ = ["cached_property"]
