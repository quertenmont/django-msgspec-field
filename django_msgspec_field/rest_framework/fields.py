"""
DRF serializer field for msgspec schemas.
"""

from __future__ import annotations

import typing as ty

import msgspec
from rest_framework import exceptions, fields

from django_msgspec_field import types

if ty.TYPE_CHECKING:
    from collections.abc import Mapping

    from rest_framework.serializers import BaseSerializer

    RequestResponseContext = Mapping[str, ty.Any]


class SchemaField(fields.Field, ty.Generic[types.ST]):
    """
    A Django REST Framework field that validates data against a msgspec schema.
    """

    adapter: types.SchemaAdapter

    def __init__(
        self,
        schema: type[types.ST],
        **kwargs,
    ):
        allow_null = kwargs.get("allow_null", False)

        self.schema = schema
        self.export_kwargs = types.SchemaAdapter.extract_export_kwargs(kwargs)
        self.adapter = types.SchemaAdapter(schema, None, None, allow_null, **self.export_kwargs)
        super().__init__(**kwargs)

    def bind(self, field_name: str, parent: BaseSerializer):
        if not self.adapter.is_bound:
            self.adapter.bind(type(parent), field_name)
        super().bind(field_name, parent)

    def to_internal_value(self, data: ty.Any):
        try:
            if isinstance(data, (str, bytes)):
                return self.adapter.validate_json(data)
            return self.adapter.validate_python(data)
        except msgspec.ValidationError as exc:
            raise exceptions.ValidationError(str(exc), code="invalid")
        except msgspec.DecodeError as exc:
            raise exceptions.ValidationError(str(exc), code="invalid")

    def to_representation(self, value: ty.Optional[types.ST]):
        try:
            prep_value = self.adapter.validate_python(value)
            return self.adapter.dump_python(prep_value)
        except msgspec.ValidationError as exc:
            raise exceptions.ValidationError(str(exc), code="invalid")
