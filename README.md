# Django + msgspec = 🖤

[![](https://img.shields.io/pypi/pyversions/django-msgspec-field.svg?color=3776AB&logo=python&logoColor=white)](https://www.python.org/)
[![](https://img.shields.io/pypi/djversions/django-msgspec-field?color=0C4B33&logo=django&logoColor=white&label=django)](https://www.djangoproject.com/)

[![](https://img.shields.io/pypi/v/django-msgspec-field.svg?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/django-msgspec-field/)
[![](https://static.pepy.tech/badge/django-msgspec-field/month)](https://pepy.tech/project/django-msgspec-field)
[![](https://img.shields.io/github/stars/quertenmont/django-msgspec-field?logo=github&style=flat)](https://github.com/quertenmont/django-msgspec-field/stargazers)
[![](https://img.shields.io/pypi/l/django-msgspec-field.svg?color=blue)](https://github.com/quertenmont/django-msgspec-field/blob/main/LICENSE)

[![](https://results.pre-commit.ci/badge/github/quertenmont/django-msgspec-field/main.svg)](https://results.pre-commit.ci/latest/github/quertenmont/django-msgspec-field/main)
[![](https://img.shields.io/github/actions/workflow/status/quertenmont/django-msgspec-field/python-test.yml?branch=main&label=build&logo=github)](https://github.com/quertenmont/django-msgspec-field)
[![](https://codecov.io/gh/quertenmont/django-msgspec-field/branch/main/graph/badge.svg)](https://codecov.io/gh/quertenmont/django-msgspec-field)
[![](https://img.shields.io/badge/type%20checked-mypy-blue.svg?logo=python)](https://mypy-lang.org/)
[![](https://img.shields.io/badge/code%20style-ruff-000000.svg?logo=ruff&logoColor=D7FF64)](https://github.com/astral-sh/ruff)

Django JSONField with msgspec structs as a Schema.

> **Note**: This library is a fork of [django-pydantic-field](https://github.com/surenkov/django-pydantic-field) that replaces Pydantic with [msgspec](https://jcristharif.com/msgspec/) for faster serialization and validation.

## Why msgspec?

[msgspec](https://jcristharif.com/msgspec/) is a fast serialization library that offers:
- **High performance**: 10-75x faster than other serialization libraries
- **Low memory usage**: More memory-efficient than alternatives
- **Type validation**: Built-in support for Python type hints
- **JSON Schema generation**: Automatic schema generation for API documentation

## Installation

Install the package with pip:

```bash
pip install django-msgspec-field
```

## Usage

```python
import msgspec
from datetime import date
from uuid import UUID

from django.db import models
from django_msgspec_field import SchemaField


class Foo(msgspec.Struct):
    count: int
    size: float = 1.0


class Bar(msgspec.Struct):
    slug: str = "foo_bar"


class MyModel(models.Model):
    # Infer schema from field annotation
    foo_field: Foo = SchemaField()

    # or explicitly pass schema to the field
    bar_list: list[Bar] = SchemaField(schema=list[Bar])

    # msgspec supports many types natively
    raw_date_map: dict[int, date] = SchemaField()
    raw_uids: set[UUID] = SchemaField()


# Usage
model = MyModel(
    foo_field={"count": "5"},
    bar_list=[{}],
    raw_date_map={1: "1970-01-01"},
    raw_uids={"17a25db0-27a4-11ed-904a-5ffb17f92734"}
)
model.save()

assert model.foo_field == Foo(count=5, size=1.0)
assert model.bar_list == [Bar(slug="foo_bar")]
assert model.raw_date_map == {1: date(1970, 1, 1)}
assert model.raw_uids == {UUID("17a25db0-27a4-11ed-904a-5ffb17f92734")}
```

The schema can be any type supported by msgspec, including:
- `msgspec.Struct` classes
- `dataclasses`
- `typing.TypedDict`
- Standard Python types (`list`, `dict`, `set`, etc.)
- Unions, Optionals, and other generic types

### Forward referencing annotations

It is also possible to use `SchemaField` with forward references and string literals:

```python
class MyModel(models.Model):
    foo_field: "Foo" = SchemaField()
    bar_list: list["Bar"] = SchemaField(schema=typing.ForwardRef("list[Bar]"))


class Foo(msgspec.Struct):
    count: int
    size: float = 1.0


class Bar(msgspec.Struct):
    slug: str = "foo_bar"
```

The exact type resolution will be postponed until the initial access to the field, which usually happens on the first instantiation of the model.

The field performs checks against the passed schema during `./manage.py check` command invocation:
- `msgspec.E001`: The passed schema could not be resolved.
- `msgspec.E002`: `default=` value could not be serialized to the schema.
- `msgspec.W003`: The default value could not be reconstructed due to `include`/`exclude` configuration.

### `typing.Annotated` support

SchemaField supports `typing.Annotated[...]` expressions for adding constraints:

```python
import typing_extensions as te
import msgspec

class MyModel(models.Model):
    annotated_field: te.Annotated[int, msgspec.Meta(gt=0, title="Positive Integer")] = SchemaField()
```

## Django Forms support

Create Django forms that validate against msgspec schemas:

```python
from django import forms
from django_msgspec_field.forms import SchemaField


class Foo(msgspec.Struct):
    slug: str = "foo_bar"


class FooForm(forms.Form):
    field = SchemaField(Foo)


form = FooForm(data={"field": '{"slug": "asdf"}'})
assert form.is_valid()
assert form.cleaned_data["field"] == Foo(slug="asdf")
```

`django_msgspec_field` also supports auto-generated fields for `ModelForm` and `modelform_factory`:

```python
class MyModelForm(forms.ModelForm):
    class Meta:
        model = MyModel
        fields = ["foo_field"]

form = MyModelForm(data={"foo_field": '{"count": 5}'})
assert form.is_valid()
assert form.cleaned_data["foo_field"] == Foo(count=5)
```

### `django-jsonform` widgets

[`django-jsonform`](https://django-jsonform.readthedocs.io) offers dynamic form construction based on JSONSchema. `django_msgspec_field.forms.SchemaField` works with its widgets:

```python
from django_msgspec_field.forms import SchemaField
from django_jsonform.widgets import JSONFormWidget

class FooForm(forms.Form):
    field = SchemaField(Foo, widget=JSONFormWidget)
```

Override the default form widget for Django Admin:

```python
from django.contrib import admin
from django_jsonform.widgets import JSONFormWidget
from django_msgspec_field.fields import MsgspecSchemaField

@admin.site.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    formfield_overrides = {
        MsgspecSchemaField: {"widget": JSONFormWidget},
    }
```

## Django REST Framework support

```python
from rest_framework import generics, serializers
from django_msgspec_field.rest_framework import SchemaField, AutoSchema


class MyModelSerializer(serializers.ModelSerializer):
    foo_field = SchemaField(schema=Foo)

    class Meta:
        model = MyModel
        fields = '__all__'


class SampleView(generics.RetrieveAPIView):
    serializer_class = MyModelSerializer

    # optional support of OpenAPI schema generation for msgspec fields
    schema = AutoSchema()
```

Global approach with typed `parser` and `renderer` classes:

```python
from rest_framework import views
from rest_framework.decorators import api_view, parser_classes, renderer_classes
from django_msgspec_field.rest_framework import SchemaRenderer, SchemaParser, AutoSchema


@api_view(["POST"])
@parser_classes([SchemaParser[Foo]])
@renderer_classes([SchemaRenderer[list[Foo]]])
def foo_view(request):
    assert isinstance(request.data, Foo)

    count = request.data.count + 1
    return Response([Foo(count=count)])


class FooClassBasedView(views.APIView):
    parser_classes = [SchemaParser[Foo]]
    renderer_classes = [SchemaRenderer[list[Foo]]]

    # optional support of OpenAPI schema generation
    schema = AutoSchema()

    def get(self, request, *args, **kwargs):
        assert isinstance(request.data, Foo)
        return Response([request.data])

    def put(self, request, *args, **kwargs):
        assert isinstance(request.data, Foo)
        count = request.data.count + 1
        return Response([request.data])
```

## Migrating from django-pydantic-field

If you're migrating from `django-pydantic-field`, here are the key changes:

1. **Replace imports**:
   ```python
   # Before (pydantic)
   from django_pydantic_field import SchemaField
   import pydantic

   class Foo(pydantic.BaseModel):
       count: int

   # After (msgspec)
   from django_msgspec_field import SchemaField
   import msgspec

   class Foo(msgspec.Struct):
       count: int
   ```

2. **Schema definitions**: Replace `pydantic.BaseModel` with `msgspec.Struct`

3. **Config options**: Remove `pydantic.ConfigDict` - msgspec uses different configuration methods

4. **Validators**: Replace Pydantic validators with msgspec constraints using `msgspec.Meta`

## Contributing

To get `django-msgspec-field` up and running in development mode:

1. Clone this repo: `git clone https://github.com/quertenmont/django-msgspec-field.git`
2. Install [uv](https://docs.astral.sh/uv/): `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync --all-extras`
4. Setup `pre-commit`: `pre-commit install`
5. Run tests: `uv run pytest`
6. Run linting: `uv run ruff check .`
7. Run type checking: `uv run mypy django_msgspec_field`

---

## License

Released under [MIT License](LICENSE).

---

## Supporting

- :star: Star this project on [GitHub](https://github.com/quertenmont/django-msgspec-field)
- :octocat: Follow me on [GitHub](https://github.com/quertenmont)
- :blue_heart: Follow me on [Twitter](https://twitter.com/LoicQuertenmont)
- :moneybag: Sponsor me on [Github](https://github.com/sponsors/quertenmont)

You can also support me via:
- [Buy me a coffee](https://buymeacoffee.com/loicquerten)
- [PayPal donation](https://www.paypal.com/donate/?business=JQ7Y92B9BTCGE&no_recurring=0&currency_code=EUR)

---

## Acknowledgement

- [Savva Surenkov](https://github.com/surenkov) for the original [django-pydantic-field](https://github.com/surenkov/django-pydantic-field) library
- [Jim Crist-Harif](https://jcristharif.com/) for creating [msgspec](https://jcristharif.com/msgspec/)
- [Churkin Oleg](https://gist.github.com/Bahus/98a9848b1f8e2dcd986bf9f05dbf9c65) for his Gist as a source of inspiration
