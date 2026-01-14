"""
Django REST Framework integration for msgspec schemas.

This module provides the main exports for REST framework integration.
Import directly from here for convenience.
"""

from .rest_framework import (
    SchemaField as SchemaField,
    SchemaParser as SchemaParser,
    SchemaRenderer as SchemaRenderer,
    AutoSchema as AutoSchema,
    coreapi as coreapi,
    openapi as openapi,
)

__all__ = (
    "SchemaField",
    "SchemaParser",
    "SchemaRenderer",
    "AutoSchema",
    "coreapi",
    "openapi",
)
