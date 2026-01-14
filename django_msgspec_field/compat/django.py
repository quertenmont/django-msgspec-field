"""
Django Migration serializer helpers for msgspec types.

This module provides serializers for Django migrations to properly handle
msgspec types and generic type annotations.
"""

from __future__ import annotations

import abc
import dataclasses
import sys
import types
import typing as ty

import typing_extensions as te
from django.db.migrations.serializer import BaseSerializer, serializer_factory
from django.db.migrations.writer import MigrationWriter

from .typing import get_args, get_origin


class BaseContainer(abc.ABC):
    """Base container class for migration serialization."""

    __slot__ = ()

    @classmethod
    def unwrap(cls, value):
        if isinstance(value, BaseContainer) and type(value) is not BaseContainer:
            return value.unwrap(value)
        return value

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return all(getattr(self, attr) == getattr(other, attr) for attr in self.__slots__)
        return NotImplemented

    def __str__(self):
        return repr(self.unwrap(self))

    def __repr__(self):
        attrs = tuple(getattr(self, attr) for attr in self.__slots__)
        return f"{self.__class__.__name__}{attrs}"


class GenericContainer(BaseContainer):
    """Container for generic type annotations in migrations."""

    __slots__ = "origin", "args"

    def __init__(self, origin, args: tuple = ()):
        self.origin = origin
        self.args = args

    @classmethod
    def wrap(cls, value):
        # Handle Annotated aliases
        if isinstance(value, AnnotatedAlias):
            args = (value.__origin__, *value.__metadata__)
            wrapped_args = tuple(map(cls.wrap, args))
            return cls(te.Annotated, wrapped_args)
        if isinstance(value, GenericTypes):
            wrapped_args = tuple(map(cls.wrap, get_args(value)))
            return cls(get_origin(value), wrapped_args)
        return value

    @classmethod
    def unwrap(cls, value):
        if not isinstance(value, cls):
            return value

        origin = value.origin

        if not value.args:
            return origin

        unwrapped_args = tuple(map(BaseContainer.unwrap, value.args))

        # Special handling for UnionType - must use | operator to reconstruct
        if origin is types.UnionType:
            result = unwrapped_args[0]
            for arg in unwrapped_args[1:]:
                result = result | arg
            return result

        try:
            return origin[unwrapped_args]
        except TypeError:
            return types.GenericAlias(origin, unwrapped_args)

    def __eq__(self, other):
        if isinstance(other, GenericTypes):
            return self == self.wrap(other)
        return super().__eq__(other)


class DataclassContainer(BaseContainer):
    """Container for dataclass instances in migrations."""

    __slots__ = "datacls", "kwargs"

    def __init__(self, datacls: type, kwargs: ty.Dict[str, ty.Any]):
        self.datacls = datacls
        self.kwargs = kwargs

    @classmethod
    def wrap(cls, value):
        if cls._is_dataclass_instance(value):
            return cls(type(value), dataclasses.asdict(value))
        if isinstance(value, GenericTypes):
            return GenericContainer.wrap(value)
        return value

    @classmethod
    def unwrap(cls, value):
        if isinstance(value, cls):
            return value.datacls(**value.kwargs)
        return value

    @staticmethod
    def _is_dataclass_instance(obj: ty.Any):
        return dataclasses.is_dataclass(obj) and not isinstance(obj, type)

    def __eq__(self, other):
        if self._is_dataclass_instance(other):
            return self == self.wrap(other)
        return super().__eq__(other)


class BaseContainerSerializer(BaseSerializer):
    """Serializer for BaseContainer instances."""

    value: BaseContainer

    def serialize(self):
        tp_repr, imports = serializer_factory(type(self.value)).serialize()
        attrs = []

        for attr in self._iter_container_attrs():
            attr_repr, attr_imports = serializer_factory(attr).serialize()
            attrs.append(attr_repr)
            imports.update(attr_imports)

        attrs_repr = ", ".join(attrs)
        return f"{tp_repr}({attrs_repr})", imports

    def _iter_container_attrs(self):
        container = self.value
        for attr in container.__slots__:
            yield getattr(container, attr)


class DataclassContainerSerializer(BaseSerializer):
    """Serializer for DataclassContainer instances."""

    value: DataclassContainer

    def serialize(self):
        tp_repr, imports = serializer_factory(self.value.datacls).serialize()

        kwarg_pairs = []
        for arg, value in self.value.kwargs.items():
            value_repr, value_imports = serializer_factory(value).serialize()
            kwarg_pairs.append(f"{arg}={value_repr}")
            imports.update(value_imports)

        kwargs_repr = ", ".join(kwarg_pairs)
        return f"{tp_repr}({kwargs_repr})", imports


class TypingSerializer(BaseSerializer):
    """Serializer for typing module types."""

    def serialize(self):
        value = GenericContainer.wrap(self.value)
        if isinstance(value, GenericContainer):
            return serializer_factory(value).serialize()

        orig_module = self.value.__module__
        orig_repr = repr(self.value)

        if not orig_repr.startswith(orig_module):
            orig_repr = f"{orig_module}.{orig_repr}"

        return orig_repr, {f"import {orig_module}"}


AnnotatedAlias = te._AnnotatedAlias

if sys.version_info >= (3, 14):
    GenericTypes: ty.Tuple[ty.Any, ...] = (types.GenericAlias, type(ty.List[int]), type(ty.List), ty.Union)
elif sys.version_info >= (3, 10):
    GenericTypes = (
        types.GenericAlias,
        type(ty.List[int]),
        type(ty.List),
        type(ty.Union[int, str]),
        types.UnionType,
    )
else:
    GenericTypes = (
        types.GenericAlias,
        type(ty.List[int]),
        type(ty.List),
        type(ty.Union[int, str]),
    )


# BaseContainerSerializer *must be* registered after all specialized container serializers
MigrationWriter.register_serializer(DataclassContainer, DataclassContainerSerializer)
MigrationWriter.register_serializer(BaseContainer, BaseContainerSerializer)

# Typing serializers
for type_ in GenericTypes:
    MigrationWriter.register_serializer(type_, TypingSerializer)

MigrationWriter.register_serializer(ty.ForwardRef, TypingSerializer)
MigrationWriter.register_serializer(type(ty.Union), TypingSerializer)  # type: ignore
MigrationWriter.register_serializer(ty._SpecialForm, TypingSerializer)  # type: ignore


if sys.version_info >= (3, 10):
    UnionType = (types.UnionType, type(ty.Union[int, str]))
else:
    UnionType = (type(ty.Union[int, str]),)


class UnionTypeSerializer(BaseSerializer):
    """Serializer for Union types."""

    value: ty.Any

    def serialize(self):
        imports = set()
        if isinstance(self.value, (type(ty.Union), *UnionType)):  # type: ignore
            imports.add("import typing")

        for arg in get_args(self.value):
            _, arg_imports = serializer_factory(arg).serialize()
            imports.update(arg_imports)

        return repr(self.value), imports


for union_type in UnionType:
    MigrationWriter.register_serializer(union_type, UnionTypeSerializer)


# msgspec.Meta serializer
try:
    import msgspec

    class MsgspecMetaSerializer(BaseSerializer):
        """Serializer for msgspec.Meta instances."""

        value: msgspec.Meta

        def serialize(self):
            imports = {"import msgspec"}

            # Get the Meta arguments as kwargs
            meta = self.value
            kwargs = {}

            # Check all possible Meta fields
            for field_name in (
                "gt",
                "ge",
                "lt",
                "le",
                "multiple_of",
                "pattern",
                "min_length",
                "max_length",
                "tz",
                "title",
                "description",
                "examples",
                "extra_json_schema",
            ):
                field_value = getattr(meta, field_name, None)
                if field_value is not None:
                    kwargs[field_name] = field_value

            kwarg_parts = []
            for k, v in kwargs.items():
                v_repr, v_imports = serializer_factory(v).serialize()
                kwarg_parts.append(f"{k}={v_repr}")
                imports.update(v_imports)

            kwargs_str = ", ".join(kwarg_parts)
            return f"msgspec.Meta({kwargs_str})", imports

    MigrationWriter.register_serializer(msgspec.Meta, MsgspecMetaSerializer)
except ImportError:
    pass
