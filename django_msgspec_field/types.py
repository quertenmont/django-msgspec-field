"""
Core types and schema adapter for msgspec integration with Django.
"""

from __future__ import annotations

import sys
import typing as ty
from collections import ChainMap

import msgspec
import typing_extensions as te

from .compat.django import BaseContainer, GenericContainer
from .compat.functools import cached_property

if ty.TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from django.db.models import Model

    DjangoModelType = ty.Type[Model]
    SchemaT = ty.Union[
        msgspec.Struct,
        Sequence[ty.Any],
        Mapping[str, ty.Any],
        set[ty.Any],
        frozenset[ty.Any],
    ]

ST = ty.TypeVar("ST", bound="SchemaT")


class ExportKwargs(te.TypedDict, total=False):
    """Export options for msgspec serialization."""

    # Encoding options
    enc_hook: ty.Callable[[ty.Any], ty.Any] | None
    # Decoding options
    dec_hook: ty.Callable[[type, ty.Any], ty.Any] | None
    strict: bool
    # For filtering fields (custom implementation)
    include: set[str] | None
    exclude: set[str] | None
    by_alias: bool
    exclude_none: bool
    exclude_defaults: bool
    exclude_unset: bool


class ImproperlyConfiguredSchema(ValueError):
    """Raised when the schema is improperly configured."""


class SchemaAdapter(ty.Generic[ST]):
    """
    Adapter class that bridges msgspec with Django's JSONField.
    Handles validation, serialization, and deserialization of msgspec types.
    """

    def __init__(
        self,
        schema: ty.Any,
        parent_type: type | None,
        attname: str | None,
        allow_null: bool | None = None,
        **export_kwargs: ty.Unpack[ExportKwargs],
    ):
        self.schema = BaseContainer.unwrap(schema)
        self.parent_type = parent_type
        self.attname = attname
        self.allow_null = allow_null
        self.export_kwargs = export_kwargs

    @classmethod
    def from_type(
        cls,
        schema: ty.Any,
        **kwargs: ty.Unpack[ExportKwargs],
    ) -> SchemaAdapter[ST]:
        """Create an adapter from a type."""
        return cls(schema, None, None, **kwargs)

    @classmethod
    def from_annotation(
        cls,
        parent_type: type,
        attname: str,
        **kwargs: ty.Unpack[ExportKwargs],
    ) -> SchemaAdapter[ST]:
        """Create an adapter from a type annotation."""
        return cls(None, parent_type, attname, **kwargs)

    @staticmethod
    def extract_export_kwargs(kwargs: dict[str, ty.Any]) -> ExportKwargs:
        """Extract the export kwargs from the kwargs passed to the field.
        This method mutates passed kwargs by removing those that are used by the adapter."""
        common_keys = kwargs.keys() & ExportKwargs.__annotations__.keys()
        export_kwargs = {key: kwargs.pop(key) for key in common_keys}
        return ty.cast(ExportKwargs, export_kwargs)

    @cached_property
    def _encoder(self) -> msgspec.json.Encoder:
        """Create a msgspec JSON encoder."""
        enc_hook = self.export_kwargs.get("enc_hook")
        return msgspec.json.Encoder(enc_hook=enc_hook)

    @cached_property
    def _decoder(self) -> msgspec.json.Decoder:
        """Create a msgspec JSON decoder for the prepared schema."""
        dec_hook = self.export_kwargs.get("dec_hook")
        strict = self.export_kwargs.get("strict", False)
        return msgspec.json.Decoder(self.prepared_schema, dec_hook=dec_hook, strict=strict)

    @property
    def is_bound(self) -> bool:
        """Return True if the adapter is bound to a specific attribute of a `parent_type`."""
        return self.parent_type is not None and self.attname is not None

    def bind(self, parent_type: type | None, attname: str | None) -> te.Self:
        """Bind the adapter to specific attribute of a `parent_type`."""
        self.parent_type = parent_type
        self.attname = attname
        self.__dict__.pop("prepared_schema", None)
        self.__dict__.pop("_decoder", None)
        self.__dict__.pop("_encoder", None)
        return self

    def validate_schema(self) -> None:
        """Validate the schema and raise an exception if it is invalid."""
        try:
            self._prepare_schema()
        except Exception as exc:
            if not isinstance(exc, ImproperlyConfiguredSchema):
                raise ImproperlyConfiguredSchema(*exc.args) from exc
            raise

    def validate_python(self, value: ty.Any, *, strict: bool | None = None) -> ST:
        """Validate a Python value against the schema."""
        if value is None and self.allow_null:
            return value  # type: ignore

        # Use msgspec.convert for Python object validation
        dec_hook = self.export_kwargs.get("dec_hook")
        if strict is None:
            strict = self.export_kwargs.get("strict", False)
        try:
            return msgspec.convert(value, self.prepared_schema, dec_hook=dec_hook, strict=strict)
        except msgspec.ValidationError:
            raise

    def validate_json(self, value: str | bytes, *, strict: bool | None = None) -> ST:
        """Validate a JSON string/bytes against the schema."""
        if isinstance(value, str):
            value = value.encode("utf-8")
        try:
            return self._decoder.decode(value)
        except msgspec.DecodeError:
            raise
        except msgspec.ValidationError:  # type: ignore
            raise

    def dump_python(self, value: ty.Any, **override_kwargs) -> ty.Any:
        """Dump the value to a JSON-compatible Python object."""
        if value is None:
            return None

        # Apply field filtering if configured
        result = msgspec.to_builtins(value, enc_hook=self.export_kwargs.get("enc_hook"))

        # Apply include/exclude filters
        # Use sentinel to distinguish between "not passed" and "explicitly set to None"
        _unset = object()
        include = override_kwargs.get("include", _unset)
        if include is _unset:
            include = self.export_kwargs.get("include")
        exclude = override_kwargs.get("exclude", _unset)
        if exclude is _unset:
            exclude = self.export_kwargs.get("exclude")
        exclude_none = override_kwargs.get("exclude_none", self.export_kwargs.get("exclude_none", False))
        exclude_defaults = override_kwargs.get("exclude_defaults", self.export_kwargs.get("exclude_defaults", False))

        if isinstance(result, dict):
            result = self._filter_dict(result, include, exclude, exclude_none, exclude_defaults, value)

        return result

    def dump_json(self, value: ty.Any, **override_kwargs) -> bytes:
        """Dump the value to JSON bytes."""
        if value is None:
            return b"null"

        # First convert to a filtered dict if needed
        python_value = self.dump_python(value, **override_kwargs)
        return msgspec.json.encode(python_value)

    def json_schema(self) -> dict[str, ty.Any]:
        """Return the JSON schema for the field."""
        return msgspec.json.schema(self.prepared_schema)

    def get_default_value(self) -> ST | None:
        """Get the default value for the schema if available."""
        schema = self.prepared_schema
        if hasattr(schema, "__struct_defaults__"):
            # For Struct types, we can try to instantiate with defaults
            try:
                return schema()  # type: ignore
            except TypeError:
                return None
        return None

    def _prepare_schema(self) -> type[ST]:
        """Prepare the schema for the adapter.

        This method is called by `prepared_schema` property and should not be called directly.
        The intent is to resolve the real schema from annotations or forward references.
        """
        schema = self.schema

        if schema is None and self.is_bound:
            schema = self._guess_schema_from_annotations()
        if isinstance(schema, str):
            schema = ty.ForwardRef(schema)

        schema = self._resolve_schema_forward_ref(schema)
        if schema is None:
            if self.is_bound:
                error_msg = f"Annotation is not provided for {self.parent_type.__name__}.{self.attname}"  # type: ignore[union-attr]
            else:
                error_msg = "Cannot resolve the schema. The adapter is accessed before it was bound."
            raise ImproperlyConfiguredSchema(error_msg)

        if self.allow_null:
            schema = ty.Optional[schema]  # type: ignore

        return ty.cast(ty.Type[ST], schema)

    prepared_schema = cached_property(_prepare_schema)

    def __copy__(self):
        instance = self.__class__(
            self.schema,
            self.parent_type,
            self.attname,
            self.allow_null,
            **self.export_kwargs,
        )
        instance.__dict__.update(self.__dict__)
        return instance

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(bound={self.is_bound}, schema={self.schema!r})"

    def __eq__(self, other: ty.Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented

        self_fields: list[ty.Any] = [self.attname, self.export_kwargs]
        other_fields: list[ty.Any] = [other.attname, other.export_kwargs]
        try:
            self_fields.append(self.prepared_schema)
            other_fields.append(other.prepared_schema)
        except ImproperlyConfiguredSchema:
            if self.is_bound and other.is_bound:
                return False
            else:
                self_fields.extend((self.schema, self.allow_null))
                other_fields.extend((other.schema, other.allow_null))

        return self_fields == other_fields

    def _guess_schema_from_annotations(self) -> type[ST] | str | ty.ForwardRef | None:
        return get_annotated_type(self.parent_type, self.attname)

    def _resolve_schema_forward_ref(self, schema: ty.Any) -> ty.Any:
        if schema is None:
            return None

        if isinstance(schema, ty.ForwardRef):
            globalns = get_namespace(self.parent_type)
            return evaluate_forward_ref(schema, globalns)

        wrapped_schema = GenericContainer.wrap(schema)
        if not isinstance(wrapped_schema, GenericContainer):
            return schema

        origin = self._resolve_schema_forward_ref(wrapped_schema.origin)
        args = map(self._resolve_schema_forward_ref, wrapped_schema.args)
        return GenericContainer.unwrap(GenericContainer(origin, tuple(args)))

    def _filter_dict(
        self,
        data: dict,
        include: set[str] | None,
        exclude: set[str] | None,
        exclude_none: bool,
        exclude_defaults: bool,
        original_value: ty.Any,
    ) -> dict:
        """Apply include/exclude filters to a dictionary."""
        result = {}

        # Get defaults from struct if available
        defaults = {}
        if exclude_defaults and hasattr(original_value, "__struct_defaults__"):
            defaults = original_value.__struct_defaults__

        for key, value in data.items():
            # Skip excluded keys
            if exclude and key in exclude:
                continue
            # Only include specified keys
            if include and key not in include:
                continue
            # Skip None values if configured
            if exclude_none and value is None:
                continue
            # Skip default values if configured
            if exclude_defaults and key in defaults and value == defaults[key]:
                continue
            result[key] = value

        return result


# Utility functions (moved from utils.py)


def get_annotations(obj: ty.Any) -> dict[str, ty.Any]:
    """Get annotations from an object."""
    try:
        from annotationlib import get_annotations as _get_annotations  # type: ignore[import-not-found]

        return _get_annotations(obj)
    except ImportError:
        if isinstance(obj, type):
            return obj.__dict__.get("__annotations__", {})
        return getattr(obj, "__annotations__", {})


def get_annotated_type(obj, field, default=None) -> ty.Any:
    """Get the type annotation for a field on an object."""
    try:
        annotations = get_annotations(obj)
        return annotations[field]
    except (AttributeError, KeyError):
        return default


def get_namespace(cls) -> ChainMap[str, ty.Any]:
    """Get the namespace for resolving forward references."""
    return ChainMap(get_local_namespace(cls), get_global_namespace(cls))


def get_global_namespace(cls) -> dict[str, ty.Any]:
    """Get the global namespace for a class."""
    try:
        module = cls.__module__
        return vars(sys.modules[module])
    except (KeyError, AttributeError):
        return {}


def get_local_namespace(cls) -> dict[str, ty.Any]:
    """Get the local namespace for a class."""
    try:
        return vars(cls)
    except TypeError:
        return {}


def get_origin_type(cls: type):
    """Get the origin type of a generic type."""
    origin_tp = ty.get_origin(cls)
    if origin_tp is not None:
        return origin_tp
    return cls


def evaluate_forward_ref(ref: ty.ForwardRef, ns: ty.Mapping[str, ty.Any]) -> ty.Any:
    """Evaluate a forward reference in a namespace."""
    # Python 3.14+ has typing.evaluate_forward_ref with keyword-only arguments
    eval_func = getattr(ty, "evaluate_forward_ref", None)
    if eval_func is not None:
        return eval_func(ref, globals=dict(ns), locals={})

    # Python 3.13+ has ForwardRef.evaluate method
    if hasattr(ref, "evaluate"):
        return ref.evaluate(globals=dict(ns), locals={})  # type: ignore

    # Fallback for older Python versions
    if sys.version_info >= (3, 13):
        return ref._evaluate(dict(ns), {}, type_params=(), recursive_guard=frozenset())
    return ref._evaluate(dict(ns), {}, recursive_guard=frozenset())
