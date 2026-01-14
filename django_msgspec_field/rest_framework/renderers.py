"""
DRF renderer for msgspec schemas.
"""

from __future__ import annotations

import typing as ty

import msgspec
from rest_framework import renderers

from django_msgspec_field import types
from . import mixins

if ty.TYPE_CHECKING:
    from collections.abc import Mapping

    RequestResponseContext = Mapping[str, ty.Any]

__all__ = ("SchemaRenderer",)


class SchemaRenderer(mixins.AnnotatedAdapterMixin[types.ST], renderers.JSONRenderer):
    """
    A DRF renderer that serializes data using msgspec schemas.
    """

    schema_context_key = "renderer_schema"
    config_context_key = "renderer_config"

    def render(self, data: ty.Any, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        if response is not None and response.exception:
            return super().render(data, accepted_media_type, renderer_context)

        adapter = self.get_adapter(renderer_context)
        if adapter is None and isinstance(data, msgspec.Struct):
            return self.render_msgspec_struct(data, renderer_context)
        if adapter is None:
            raise RuntimeError("Schema should be either explicitly set with annotation or passed in the context")

        try:
            prep_data = adapter.validate_python(data)
            return adapter.dump_json(prep_data)
        except msgspec.ValidationError as exc:
            return msgspec.json.encode({"error": str(exc)})

    def render_msgspec_struct(self, instance: msgspec.Struct, renderer_context: Mapping[str, ty.Any]):
        """Render a msgspec Struct directly."""
        return msgspec.json.encode(instance)
