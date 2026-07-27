"""
Django REST Framework integration for msgspec schemas.

This module provides the main exports for REST framework integration.
Import directly from here for convenience.
"""

from .rest_framework import (
    AutoSchema as AutoSchema,
)
from .rest_framework import (
    SchemaField as SchemaField,
)
from .rest_framework import (
    SchemaParser as SchemaParser,
)
from .rest_framework import (
    SchemaRenderer as SchemaRenderer,
)
from .rest_framework import (
    coreapi as coreapi,
)
from .rest_framework import (
    openapi as openapi,
)

__all__ = (
    "AutoSchema",
    "SchemaField",
    "SchemaParser",
    "SchemaRenderer",
    "coreapi",
    "openapi",
)
