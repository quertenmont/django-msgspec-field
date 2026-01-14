import sys
import types
import typing as t
import typing_extensions as te

from django.db.migrations.writer import MigrationWriter
import pytest

import django_msgspec_field

try:
    from django_msgspec_field.compat.django import GenericContainer
except ImportError:
    from django_msgspec_field._migration_serializers import GenericContainer  # noqa

try:
    import annotationlib
except ImportError:
    annotationlib = None

test_types = [
    str,
    list,
    list[str],
    t.Literal["foo"],
    t.Union[t.Literal["foo"], list[str]],
    list[t.Union[int, bool]],
    tuple[list[t.Literal[1]], t.Union[str, t.Literal["foo"]]],
    t.ForwardRef("str"),
]

# Add UnionType tests for Python 3.10+
if sys.version_info >= (3, 10):
    test_types.extend([
        float | None,
        int | str,
        dict[str, float | None],
        list[int | str | None],
    ])


@pytest.mark.parametrize("raw_type", test_types)
def test_wrap_unwrap_idempotent(raw_type):
    wrapped_type = GenericContainer.wrap(raw_type)
    assert raw_type == GenericContainer.unwrap(wrapped_type)


@pytest.mark.parametrize("raw_type", test_types)
def test_serialize_eval_idempotent(raw_type):
    raw_type = GenericContainer.wrap(raw_type)
    expression, _ = MigrationWriter.serialize(raw_type)
    imports = dict(
        typing=t, typing_extensions=te, django_msgspec_field=django_msgspec_field, annotationlib=annotationlib,
        types=types,
    )
    assert eval(expression, imports) == raw_type


@pytest.mark.skipif(sys.version_info < (3, 10), reason="UnionType requires Python 3.10+")
class TestUnionTypeUnwrap:
    """Tests for UnionType unwrapping fix."""

    def test_simple_union_unwrap(self):
        """Test that simple UnionType (X | Y) is correctly unwrapped."""
        container = GenericContainer(types.UnionType, (float, type(None)))
        result = GenericContainer.unwrap(container)
        assert result == float | None
        assert type(result) is types.UnionType

    def test_multi_union_unwrap(self):
        """Test that multi-type UnionType (X | Y | Z) is correctly unwrapped."""
        container = GenericContainer(types.UnionType, (int, str, type(None)))
        result = GenericContainer.unwrap(container)
        assert result == int | str | None
        assert type(result) is types.UnionType

    def test_nested_union_in_dict(self):
        """Test that UnionType nested in dict is correctly unwrapped."""
        union_container = GenericContainer(types.UnionType, (float, type(None)))
        dict_container = GenericContainer(dict, (str, union_container))
        result = GenericContainer.unwrap(dict_container)
        assert result == dict[str, float | None]

    def test_nested_union_in_list(self):
        """Test that UnionType nested in list is correctly unwrapped."""
        union_container = GenericContainer(types.UnionType, (int, str))
        list_container = GenericContainer(list, (union_container,))
        result = GenericContainer.unwrap(list_container)
        assert result == list[int | str]
