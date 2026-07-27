"""
Django REST Framework integration for msgspec schemas.
"""

from . import coreapi as coreapi
from . import openapi as openapi
from .fields import SchemaField as SchemaField
from .openapi import AutoSchema as AutoSchema
from .parsers import SchemaParser as SchemaParser
from .renderers import SchemaRenderer as SchemaRenderer

__all__ = (
    "AutoSchema",
    "SchemaField",
    "SchemaParser",
    "SchemaRenderer",
    "coreapi",
    "openapi",
)
