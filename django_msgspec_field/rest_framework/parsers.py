"""
DRF parser for msgspec schemas.
"""

from __future__ import annotations

import typing as ty

import msgspec
from rest_framework import exceptions, parsers

from django_msgspec_field import types
from . import mixins, renderers


class SchemaParser(mixins.AnnotatedAdapterMixin[types.ST], parsers.JSONParser):
    """
    A DRF parser that validates incoming JSON against a msgspec schema.
    """

    schema_context_key = "parser_schema"
    config_context_key = "parser_config"
    renderer_class = renderers.SchemaRenderer

    def parse(self, stream: ty.IO[bytes], media_type=None, parser_context=None):
        parser_context = parser_context or {}
        adapter = self.get_adapter(parser_context)
        if adapter is None:
            raise RuntimeError("Schema should be either explicitly set with annotation or passed in the context")

        try:
            return adapter.validate_json(stream.read())
        except msgspec.ValidationError as exc:
            raise exceptions.ParseError(str(exc))
        except msgspec.DecodeError as exc:
            raise exceptions.ParseError(str(exc))
