"""
Type stubs for django_msgspec_field.fields
"""

from __future__ import annotations

import typing as ty

import typing_extensions as te
from django.db.models.fields.json import JSONField
from django.db.models.expressions import BaseExpression

from .types import ST, SchemaT, ExportKwargs

class _SchemaFieldKwargs(ExportKwargs, total=False):
    name: str | None
    verbose_name: str | None
    primary_key: bool
    max_length: int | None
    unique: bool
    blank: bool
    db_index: bool
    rel: ty.Any
    editable: bool
    serialize: bool
    unique_for_date: str | None
    unique_for_month: str | None
    unique_for_year: str | None
    choices: ty.Sequence[ty.Tuple[str, str]] | None
    help_text: str | None
    db_column: str | None
    db_tablespace: str | None
    auto_created: bool
    validators: ty.Sequence[ty.Callable] | None
    error_messages: ty.Mapping[str, str] | None
    db_comment: str | None

@ty.overload
def SchemaField(
    schema: ty.Annotated[type[ST | None], ...] = ...,
    default: SchemaT | ty.Callable[[], SchemaT | None] | BaseExpression | None = ...,
    *args,
    null: ty.Literal[True],
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> ST | None: ...
@ty.overload
def SchemaField(
    schema: ty.Annotated[type[ST], ...] = ...,
    default: SchemaT | ty.Callable[[], SchemaT] | BaseExpression = ...,
    *args,
    null: ty.Literal[False] = ...,
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> ST: ...
@ty.overload
def SchemaField(
    schema: type[ST | None] | ty.ForwardRef = ...,
    default: SchemaT | ty.Callable[[], SchemaT | None] | BaseExpression | None = ...,
    *args,
    null: ty.Literal[True],
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> ST | None: ...
@ty.overload
def SchemaField(
    schema: type[ST] | ty.ForwardRef = ...,
    default: SchemaT | ty.Callable[[], SchemaT] | BaseExpression = ...,
    *args,
    null: ty.Literal[False] = ...,
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> ST: ...

class MsgspecSchemaField(JSONField, ty.Generic[ST]): ...
