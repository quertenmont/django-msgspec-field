"""
Type stubs for django_msgspec_field.forms
"""

from __future__ import annotations

import typing as ty
import typing_extensions as te

from django.forms.fields import JSONField
from django.forms.widgets import Widget

from .types import ST, ExportKwargs

class SchemaField(JSONField, ty.Generic[ST]):
    def __init__(
        self,
        schema: type[ST] | te.Annotated[type[ST], ...] | ty.ForwardRef | str,
        allow_null: bool | None = None,
        *args,
        **kwargs: te.Unpack[ExportKwargs],
    ) -> None: ...

class JSONFormSchemaWidget(Widget, ty.Generic[ST]):
    def __init__(
        self,
        schema: type[ST] | te.Annotated[type[ST], ...] | ty.ForwardRef | str,
        allow_null: bool | None = None,
        export_kwargs: ExportKwargs | None = None,
        **kwargs,
    ) -> None: ...
