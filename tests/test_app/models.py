import typing as t
import typing_extensions as te

import msgspec
from django.db import models
from django_msgspec_field import SchemaField

from ..conftest import InnerSchema


class FrozenInnerSchema(msgspec.Struct, frozen=True):
    """Frozen version of InnerSchema."""

    stub_str: str
    stub_list: t.List[str]
    stub_int: int = 1


class SampleModel(models.Model):
    sample_field: InnerSchema = SchemaField()
    sample_list: t.List[InnerSchema] = SchemaField()
    sample_seq: t.Sequence[InnerSchema] = SchemaField(schema=t.List[InnerSchema], default=list)

    class Meta:
        app_label = "test_app"


class SampleForwardRefModel(models.Model):
    annotated_field: "SampleSchema" = SchemaField(default=dict)
    field = SchemaField(schema=t.ForwardRef("SampleSchema"), default=dict)

    class Meta:
        app_label = "test_app"


class SampleSchema(msgspec.Struct):
    """Sample schema for testing."""

    field: int = 1


class ExampleSchema(msgspec.Struct):
    """Example schema for testing."""

    count: int


class ExampleModel(models.Model):
    example_field: ExampleSchema = SchemaField(default={"count": 1})


class SampleModelWithRoot(models.Model):
    root_field = SchemaField(schema=t.List[int], default=list)


class SampleModelAnnotated(models.Model):
    annotated_field: te.Annotated[t.Union[int, float], msgspec.Meta(gt=0, title="Annotated Field")] = SchemaField()
    annotated_schema = SchemaField(schema=te.Annotated[t.Union[int, float], msgspec.Meta(gt=0)])
