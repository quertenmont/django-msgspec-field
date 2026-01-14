"""
Django REST Framework integration for msgspec schemas.
"""

from . import coreapi as coreapi
from . import openapi as openapi
from .fields import SchemaField as SchemaField
from .parsers import SchemaParser as SchemaParser
from .renderers import SchemaRenderer as SchemaRenderer
from .openapi import AutoSchema as AutoSchema

__all__ = (
    "coreapi",
    "openapi",
    "SchemaField",
    "SchemaParser",
    "SchemaRenderer",
    "AutoSchema",
)
