import json
import sys
import typing as ty
from collections import abc
from copy import copy
from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.migrations.writer import MigrationWriter

from django_msgspec_field import fields

from .conftest import InnerSchema, SampleDataclass, SchemaWithCustomTypes  # noqa
from .sample_app.models import Building
from .test_app.models import SampleForwardRefModel, SampleModel, SampleSchema


@pytest.mark.parametrize(
    "exported_primitive_name",
    ["SchemaField"],
)
def test_module_imports(exported_primitive_name):
    assert exported_primitive_name in dir(fields)
    assert getattr(fields, exported_primitive_name, None) is not None


def test_sample_field():
    sample_field = fields.MsgspecSchemaField(schema=InnerSchema)
    existing_instance = InnerSchema(stub_str="abc", stub_list=[date(2022, 7, 1)])

    expected_encoded = {"stub_str": "abc", "stub_int": 1, "stub_list": ["2022-07-01"]}

    # Compare parsed JSON (key order may differ)
    db_value = sample_field.get_db_prep_value(existing_instance, connection)
    assert json.loads(db_value) == expected_encoded
    assert sample_field.to_python(expected_encoded) == existing_instance


def test_sample_field_with_raw_data():
    sample_field = fields.MsgspecSchemaField(schema=InnerSchema)
    existing_raw = {"stub_str": "abc", "stub_list": [date(2022, 7, 1)]}

    expected_encoded = {"stub_str": "abc", "stub_int": 1, "stub_list": ["2022-07-01"]}

    # Compare parsed JSON (key order may differ)
    db_value = sample_field.get_db_prep_value(existing_raw, connection)
    assert json.loads(db_value) == expected_encoded
    assert sample_field.to_python(expected_encoded) == InnerSchema(**existing_raw)


def test_null_field():
    field = fields.SchemaField(InnerSchema, null=True, default=None)
    assert field.to_python(None) is None
    assert field.get_prep_value(None) is None

    field = fields.SchemaField(ty.Optional[InnerSchema], null=True, default=None)
    assert field.get_prep_value(None) is None


def test_forwardrefs_deferred_resolution():
    obj = SampleForwardRefModel(field={}, annotated_field={})
    assert isinstance(obj.field, SampleSchema)
    assert isinstance(obj.annotated_field, SampleSchema)


@pytest.mark.parametrize(
    "forward_ref",
    [
        "InnerSchema",
        ty.ForwardRef("SampleDataclass"),
        ty.List["int"],
    ],
)
def test_resolved_forwardrefs(forward_ref, request):
    model_name = f"ModelWithForwardRefs_{request.node.name.split('[')[-1].rstrip(']')}"
    class_params = {
        "field": fields.SchemaField(),
        "__module__": "tests.test_fields",
        "Meta": type("Meta", (), {"app_label": "test_app"}),
    }
    # Dynamically annotate the field
    class_params["__annotations__"] = {"field": forward_ref}

    type(model_name, (models.Model,), class_params)


@pytest.mark.parametrize(
    "field",
    [
        fields.MsgspecSchemaField(
            schema=InnerSchema,
            default=InnerSchema(stub_str="abc", stub_list=[date(2022, 7, 1)]),
        ),
        fields.MsgspecSchemaField(
            schema=InnerSchema,
            default={"stub_str": "abc", "stub_list": [date(2022, 7, 1)]},
        ),
        fields.MsgspecSchemaField(schema=InnerSchema, null=True, default=None),
        fields.MsgspecSchemaField(
            schema=SampleDataclass,
            default={"stub_str": "abc", "stub_list": [date(2022, 7, 1)]},
        ),
        fields.MsgspecSchemaField(schema=ty.Optional[InnerSchema], null=True, default=None),
        fields.MsgspecSchemaField(schema=ty.List[str], default=[""]),
        fields.MsgspecSchemaField(schema=ty.Optional[ty.List[str]], default=[""]),
        fields.MsgspecSchemaField(schema=ty.Optional[ty.List[str]], null=True, default=None),
        fields.MsgspecSchemaField(schema=ty.Optional[ty.List[str]], null=True, blank=True),
        fields.MsgspecSchemaField(schema=SchemaWithCustomTypes, default={}),
    ],
)
def test_field_serialization(field):
    _test_field_serialization(field)


@pytest.mark.parametrize(
    "field_factory",
    [
        lambda: fields.MsgspecSchemaField(schema=list[InnerSchema], default=list),
        lambda: fields.MsgspecSchemaField(schema=dict[str, InnerSchema], default=dict),
        lambda: fields.MsgspecSchemaField(schema=abc.Sequence[InnerSchema], default=list),
        lambda: fields.MsgspecSchemaField(schema=abc.Mapping[str, InnerSchema], default=dict),
    ],
)
def test_field_builtin_annotations_serialization(field_factory):
    _test_field_serialization(field_factory())


def test_field_union_type_serialization():
    field = fields.MsgspecSchemaField(schema=(InnerSchema | None), null=True, default=None)
    _test_field_serialization(field)


@pytest.mark.parametrize(
    "old_field, new_field",
    [
        (
            lambda: fields.MsgspecSchemaField(schema=ty.List[InnerSchema], default=list),
            lambda: fields.MsgspecSchemaField(schema=list[InnerSchema], default=list),
        ),
        (
            lambda: fields.MsgspecSchemaField(schema=ty.Dict[str, InnerSchema], default=dict),
            lambda: fields.MsgspecSchemaField(schema=dict[str, InnerSchema], default=dict),
        ),
        (
            lambda: fields.MsgspecSchemaField(schema=ty.Sequence[InnerSchema], default=list),
            lambda: fields.MsgspecSchemaField(schema=abc.Sequence[InnerSchema], default=list),
        ),
        (
            lambda: fields.MsgspecSchemaField(schema=ty.Mapping[str, InnerSchema], default=dict),
            lambda: fields.MsgspecSchemaField(schema=abc.Mapping[str, InnerSchema], default=dict),
        ),
    ],
)
def test_field_typing_to_builtin_serialization(old_field, new_field):
    old_field, new_field = old_field(), new_field()

    _, _, args, kwargs = old_field.deconstruct()

    reconstructed_field = fields.MsgspecSchemaField(*args, **kwargs)
    assert old_field.get_default() == new_field.get_default() == reconstructed_field.get_default()
    assert new_field.schema == reconstructed_field.schema

    deserialized_field = reconstruct_field(serialize_field(old_field))
    assert old_field.get_default() == deserialized_field.get_default() == new_field.get_default()
    assert new_field.schema == deserialized_field.schema


@pytest.mark.parametrize(
    "field, flawed_data",
    [
        (fields.MsgspecSchemaField(schema=InnerSchema), {}),
        (fields.MsgspecSchemaField(schema=ty.List[InnerSchema]), [{}]),
        (fields.MsgspecSchemaField(schema=ty.Dict[int, float]), {"1": "abc"}),
    ],
)
def test_field_validation_exceptions(field, flawed_data):
    with pytest.raises(ValidationError):
        field.to_python(flawed_data)


def test_model_validation_exceptions():
    with pytest.raises(ValidationError):
        SampleModel(sample_field=1)
    with pytest.raises(ValidationError):
        SampleModel(sample_field={"stub_list": {}, "stub_str": ""})

    valid_initial = SampleModel(
        sample_field={"stub_list": [], "stub_str": ""},
        sample_list=[],
        sample_seq=[],
    )
    with pytest.raises(ValidationError):
        valid_initial.sample_field = 1


@pytest.mark.parametrize(
    "export_kwargs",
    [
        {"include": {"stub_str", "stub_int"}},
        {"exclude": {"stub_list"}},
        {"exclude_none": True},
    ],
)
def test_export_kwargs_support(export_kwargs):
    field = fields.MsgspecSchemaField(
        schema=InnerSchema,
        default=InnerSchema(stub_str="", stub_list=[]),
        **export_kwargs,
    )
    _test_field_serialization(field)

    existing_instance = InnerSchema(stub_str="abc", stub_list=[date(2022, 7, 1)])
    assert field.get_prep_value(existing_instance)


def _test_field_serialization(field):
    _, _, args, kwargs = field.deconstruct()

    reconstructed_field = fields.MsgspecSchemaField(*args, **kwargs)
    assert field.get_default() == reconstructed_field.get_default()

    # Compare schemas - allow for typing.List[str] == list[str] etc.
    assert _schemas_equivalent(reconstructed_field.schema, field.schema)

    deserialized_field = reconstruct_field(serialize_field(field))
    assert deserialized_field.get_default() == field.get_default()
    assert _schemas_equivalent(deserialized_field.schema, field.schema)


def _schemas_equivalent(schema1, schema2):
    """Compare schemas for equivalence, handling typing.List vs list etc."""
    if schema1 == schema2:
        return True

    # Get origins and args for generic types
    origin1 = ty.get_origin(schema1)
    origin2 = ty.get_origin(schema2)
    args1 = ty.get_args(schema1)
    args2 = ty.get_args(schema2)

    # Handle list vs typing.List, dict vs typing.Dict etc
    if origin1 is not None and origin2 is not None:
        # Normalize origins (typing.List -> list, typing.Dict -> dict, etc.)
        normalized_origin1 = origin1 if not hasattr(origin1, "__mro__") else origin1
        normalized_origin2 = origin2 if not hasattr(origin2, "__mro__") else origin2

        # Compare list/List, dict/Dict, etc.
        if normalized_origin1 == normalized_origin2 or (
            # list vs typing.List
            (normalized_origin1 is list and origin2 is list)
            or (normalized_origin2 is list and origin1 is list)
            or (normalized_origin1 is dict and origin2 is dict)
            or (normalized_origin2 is dict and origin1 is dict)
        ):
            if len(args1) != len(args2):
                return False
            return all(_schemas_equivalent(a1, a2) for a1, a2 in zip(args1, args2))

    # Handle Union types (including Optional)
    if origin1 is ty.Union and origin2 is ty.Union:
        # Sort args to handle order differences
        sorted_args1 = sorted(args1, key=str)
        sorted_args2 = sorted(args2, key=str)
        if len(sorted_args1) != len(sorted_args2):
            return False
        return all(_schemas_equivalent(a1, a2) for a1, a2 in zip(sorted_args1, sorted_args2))

    return False


def serialize_field(field: fields.MsgspecSchemaField) -> str:
    serialized_field, _ = MigrationWriter.serialize(field)
    return serialized_field


def reconstruct_field(field_repr: str) -> fields.MsgspecSchemaField:
    return eval(field_repr, globals(), sys.modules)


def test_copy_field():
    copied = copy(Building.meta.field)

    assert copied.name == Building.meta.field.name
    assert copied.attname == Building.meta.field.attname
    assert copied.concrete == Building.meta.field.concrete


def test_model_init_no_default():
    try:
        SampleModel()
    except Exception:
        pytest.fail("Model with schema field without a default value should be able to initialize")
