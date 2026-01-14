"""
Type stubs for django_msgspec_field.rest_framework
"""

from __future__ import annotations

import typing as ty
import typing_extensions as te

from rest_framework import fields as drf_fields
from rest_framework import parsers, renderers
from rest_framework.schemas import openapi

from .types import ST, ExportKwargs

class SchemaField(drf_fields.Field, ty.Generic[ST]):
    def __init__(
        self,
        schema: type[ST],
        **kwargs: te.Unpack[ExportKwargs],
    ) -> None: ...

class SchemaParser(parsers.JSONParser, ty.Generic[ST]): ...
class SchemaRenderer(renderers.JSONRenderer, ty.Generic[ST]): ...
class AutoSchema(openapi.AutoSchema): ...
