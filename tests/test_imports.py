import pytest

import django_msgspec_field
from django_msgspec_field import fields, forms, rest_framework


@pytest.mark.parametrize(
    "module, exported_primitive_name",
    [
        (django_msgspec_field, "SchemaField"),
        (fields, "SchemaField"),
        (forms, "SchemaField"),
        (rest_framework, "SchemaParser"),
        (rest_framework, "SchemaRenderer"),
        (rest_framework, "SchemaField"),
        (rest_framework, "AutoSchema"),
        (rest_framework, "openapi"),
        (rest_framework, "coreapi"),
    ],
)
def test_module_imports(module, exported_primitive_name):
    assert exported_primitive_name in dir(module)
    assert getattr(module, exported_primitive_name, None) is not None
