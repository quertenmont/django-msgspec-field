"""
Django model field for storing msgspec-validated JSON data.
"""

from __future__ import annotations

import json
import typing as ty

import msgspec
import typing_extensions as te
from django.core import checks, exceptions
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.expressions import BaseExpression, Col, Value
from django.db.models.fields import NOT_PROVIDED
from django.db.models.fields.json import JSONField, KeyTransform
from django.db.models.lookups import Transform
from django.db.models.query_utils import DeferredAttribute

from .compat.django import BaseContainer, GenericContainer
from . import forms, types

if ty.TYPE_CHECKING:
    import json

    from django.db.models import Model

    class _SchemaFieldKwargs(types.ExportKwargs, total=False):
        # django.db.models.fields.Field kwargs
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
        # django.db.models.fields.json.JSONField kwargs
        encoder: ty.Callable[[], json.JSONEncoder]
        decoder: ty.Callable[[], json.JSONDecoder]


__all__ = ("SchemaField", "MsgspecSchemaField")


class SchemaAttribute(DeferredAttribute):
    field: MsgspecSchemaField

    def __set_name__(self, owner, name):
        self.field.adapter.bind(owner, name)

    def __set__(self, obj, value):
        obj.__dict__[self.field.attname] = self.field.to_python(value)


class UninitializedSchemaAttribute(SchemaAttribute):
    def __set__(self, obj, value):
        if value is not None:
            value = self.field.to_python(value)
        obj.__dict__[self.field.attname] = value


class MsgspecSchemaField(JSONField, ty.Generic[types.ST]):
    """
    A Django JSONField that validates data against a msgspec schema.

    This field stores JSON data in the database and validates/converts it
    using msgspec for type-safe serialization and deserialization.
    """

    adapter: types.SchemaAdapter

    def __init__(
        self,
        *args,
        schema: type[types.ST] | te.Annotated[type[types.ST], ...] | BaseContainer | ty.ForwardRef | str | None = None,
        **kwargs,
    ):
        kwargs.setdefault("encoder", DjangoJSONEncoder)
        self.export_kwargs = export_kwargs = types.SchemaAdapter.extract_export_kwargs(kwargs)
        super().__init__(*args, **kwargs)

        self.schema = BaseContainer.unwrap(schema)
        self.adapter = types.SchemaAdapter(schema, None, self.get_attname(), self.null, **export_kwargs)

    def __copy__(self):
        _, _, args, kwargs = self.deconstruct()
        copied = self.__class__(*args, **kwargs)
        copied.set_attributes_from_name(self.name)
        return copied

    def deconstruct(self) -> ty.Any:
        field_name, import_path, args, kwargs = super().deconstruct()

        # Normalize the import path
        if import_path.startswith("django_msgspec_field."):
            import_path = import_path.replace("django_msgspec_field.", "django_msgspec_field.", 1)

        default = kwargs.get("default", NOT_PROVIDED)
        if default is not NOT_PROVIDED and not callable(default):
            kwargs["default"] = self._prepare_raw_value(default, include=None, exclude=None)

        # Get the schema - try prepared_schema first (if adapter is bound), otherwise use original
        schema = self.schema
        if (schema is None or isinstance(schema, (ty.ForwardRef, str))) and self.adapter.is_bound:
            try:
                schema = self.adapter.prepared_schema
            except types.ImproperlyConfiguredSchema:
                pass
        prep_schema = GenericContainer.wrap(schema)
        kwargs.update(schema=prep_schema, **self.export_kwargs)

        return field_name, import_path, args, kwargs

    @staticmethod
    def descriptor_class(field: MsgspecSchemaField) -> DeferredAttribute:
        if field.has_default():
            return SchemaAttribute(field)
        return UninitializedSchemaAttribute(field)

    def contribute_to_class(self, cls: types.DjangoModelType, name: str, private_only: bool = False) -> None:
        self.adapter.bind(cls, name)
        super().contribute_to_class(cls, name, private_only)

    def check(self, **kwargs: ty.Any) -> list[checks.CheckMessage]:
        # Remove checks of using mutable datastructure instances as `default` values
        performed_checks = [check for check in super().check(**kwargs) if check.id != "fields.E010"]
        try:
            # Test that the schema could be resolved in runtime
            self.adapter.validate_schema()
        except types.ImproperlyConfiguredSchema as exc:
            message = f"Cannot resolve the schema. Original error: \n{exc.args[0]}"
            performed_checks.append(checks.Error(message, obj=self, id="msgspec.E001"))

        try:
            # Test that the default value conforms to the schema.
            if self.has_default():
                self.get_prep_value(self.get_default())
        except msgspec.ValidationError as exc:
            message = f"Default value cannot be adapted to the schema. msgspec error: \n{str(exc)}"
            performed_checks.append(checks.Error(message, obj=self, id="msgspec.E002"))

        if {"include", "exclude"} & self.export_kwargs.keys():
            # Try to prepare the default value to test export ability against it.
            schema_default = self.get_default()
            if schema_default is None:
                # If the default value is not set, try to get the default value from the schema.
                prep_value = self.adapter.get_default_value()
                if prep_value is not None:
                    schema_default = prep_value

            if schema_default is not None:
                try:
                    # Perform the full round-trip transformation to test the export ability.
                    self.adapter.validate_python(self.get_prep_value(schema_default))
                except msgspec.ValidationError as exc:
                    message = f"Export arguments may lead to data integrity problems. msgspec error: \n{str(exc)}"
                    hint = "Please review `include` and `exclude` arguments."
                    performed_checks.append(checks.Warning(message, obj=self, hint=hint, id="msgspec.W003"))

        return performed_checks

    def validate(self, value: ty.Any, model_instance: ty.Any) -> None:
        value = self.adapter.validate_python(value)
        return super(JSONField, self).validate(value, model_instance)

    def to_python(self, value: ty.Any):
        # Only try validate_json if value is a string/bytes
        if isinstance(value, (str, bytes)):
            try:
                value = self.adapter.validate_json(value)
                return value
            except (ValueError, msgspec.DecodeError, msgspec.ValidationError):
                """This is an expected error, this step is required to parse serialized values."""

        try:
            return self.adapter.validate_python(value)
        except msgspec.ValidationError as exc:
            raise exceptions.ValidationError(str(exc), code="invalid") from exc

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value

        # Some backends (SQLite at least) extract non-string values in their SQL datatypes.
        if isinstance(expression, KeyTransform):
            return super().from_db_value(value, expression, connection)

        try:
            return self.adapter.validate_json(value)
        except (ValueError, msgspec.DecodeError, msgspec.ValidationError):
            return super().from_db_value(value, expression, connection)

    def get_prep_value(self, value: ty.Any):
        value = self._prepare_raw_value(value)
        return super().get_prep_value(value)

    def get_transform(self, lookup_name: str):
        transform: ty.Any = super().get_transform(lookup_name)
        if transform is not None:
            transform = SchemaKeyTransformAdapter(transform)
        return transform

    def get_default(self) -> ty.Any:
        default_value = super().get_default()
        if self.has_default():
            return self.adapter.validate_python(default_value)
        return default_value

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        field_kwargs = dict(
            form_class=form_class or forms.SchemaField,
            choices_form_class=choices_form_class,
            schema=self.adapter.prepared_schema,
            **self.export_kwargs,
        )
        field_kwargs.update(kwargs)
        return super().formfield(**field_kwargs)  # type: ignore

    def value_to_string(self, obj: Model):
        value = super().value_from_object(obj)
        return self._prepare_raw_value(value)

    def _prepare_raw_value(self, value: ty.Any, **dump_kwargs):
        if isinstance(value, Value) and isinstance(value.output_field, self.__class__):
            # Prepare inner value for `Value`-wrapped expressions.
            value = Value(self._prepare_raw_value(value.value), value.output_field)
        elif not isinstance(value, BaseExpression):
            # Prepare the value if it is not a query expression.
            try:
                value = self.adapter.validate_python(value)
            except (msgspec.ValidationError, types.ImproperlyConfiguredSchema):
                """This is a legitimate situation, the data could not be initially coerced
                or the adapter is not yet bound (e.g., during migration generation)."""
            value = self.adapter.dump_python(value, **dump_kwargs)

        return value


class SchemaKeyTransformAdapter:
    """An adapter for creating key transforms for schema field lookups."""

    def __init__(self, transform: type[Transform]):
        self.transform = transform

    def __call__(self, col: Col | None = None, *args, **kwargs) -> Transform | None:
        """All transforms should bypass the SchemaField's adaptation with `get_prep_value`,
        and routed to JSONField's `get_prep_value` for further processing."""
        if isinstance(col, BaseExpression):
            col = col.copy()
            col.output_field = super(MsgspecSchemaField, col.output_field)  # type: ignore
        return self.transform(col, *args, **kwargs)


# Type overloads for better IDE support
@ty.overload
def SchemaField(
    schema: ty.Annotated[type[types.ST | None], ...] = ...,
    default: types.SchemaT | ty.Callable[[], types.SchemaT | None] | BaseExpression | None = ...,
    *args,
    null: ty.Literal[True],
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> types.ST | None: ...


@ty.overload
def SchemaField(
    schema: ty.Annotated[type[types.ST], ...] = ...,
    default: types.SchemaT | ty.Callable[[], types.SchemaT] | BaseExpression = ...,
    *args,
    null: ty.Literal[False] = ...,
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> types.ST: ...


@ty.overload
def SchemaField(
    schema: type[types.ST | None] | ty.ForwardRef = ...,
    default: types.SchemaT | ty.Callable[[], types.SchemaT | None] | BaseExpression | None = ...,
    *args,
    null: ty.Literal[True],
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> types.ST | None: ...


@ty.overload
def SchemaField(
    schema: type[types.ST] | ty.ForwardRef = ...,
    default: types.SchemaT | ty.Callable[[], types.SchemaT] | BaseExpression = ...,
    *args,
    null: ty.Literal[False] = ...,
    **kwargs: te.Unpack[_SchemaFieldKwargs],
) -> types.ST: ...


def SchemaField(schema=None, default=NOT_PROVIDED, *args, **kwargs):  # type: ignore
    """
    Create a schema-validated JSON field.

    This is the main entry point for creating msgspec-validated JSON fields
    in Django models.

    Args:
        schema: The msgspec type to validate against. Can be a Struct, dataclass,
                or any type supported by msgspec.
        default: Default value for the field.
        **kwargs: Additional field options passed to JSONField.

    Returns:
        A MsgspecSchemaField instance.
    """
    return MsgspecSchemaField(*args, schema=schema, default=default, **kwargs)
