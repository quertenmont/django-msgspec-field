"""
Django REST Framework integration for msgspec schemas.

This module provides the main exports for REST framework integration.
Import directly from here for convenience.
"""

from .rest_framework import (
    AutoSchema,
    SchemaField,
    SchemaParser,
    SchemaRenderer,
    coreapi,
    openapi,
)

__all__ = (
    "AutoSchema",
    "SchemaField",
    "SchemaParser",
    "SchemaRenderer",
    "coreapi",
    "openapi",
)
