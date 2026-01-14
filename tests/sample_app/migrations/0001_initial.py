# Generated migration for django-msgspec-field

import django.core.serializers.json
from django.db import migrations, models
import django_msgspec_field.compat.django
import django_msgspec_field.fields
import tests.sample_app.models
import typing
import typing_extensions


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Building",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "opt_meta",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default={"type": "frame"},
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        exclude={"type"},
                        null=True,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            typing.Union,
                            (
                                tests.sample_app.models.BuildingMeta,
                                type(None),
                            ),
                        ),
                    ),
                ),
                (
                    "meta",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default={"type": "frame"},
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        include={"type"},
                        schema=tests.sample_app.models.BuildingMeta,
                    ),
                ),
                (
                    "meta_schema_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            list, (tests.sample_app.models.BuildingMeta,)
                        ),
                    ),
                ),
                (
                    "meta_typing_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            list, (tests.sample_app.models.BuildingMeta,)
                        ),
                    ),
                ),
                (
                    "meta_untyped_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, schema=list
                    ),
                ),
                (
                    "meta_untyped_builtin_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, schema=list
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PostponedBuilding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "meta",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default={"type": "frame"},
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=tests.sample_app.models.BuildingMeta,
                    ),
                ),
                (
                    "meta_builtin_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            list, (tests.sample_app.models.BuildingMeta,)
                        ),
                    ),
                ),
                (
                    "meta_typing_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list,
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            list, (tests.sample_app.models.BuildingMeta,)
                        ),
                    ),
                ),
                (
                    "meta_untyped_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, schema=list
                    ),
                ),
                (
                    "meta_untyped_builtin_list",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        default=list, encoder=django.core.serializers.json.DjangoJSONEncoder, schema=list
                    ),
                ),
                (
                    "nested_generics",
                    django_msgspec_field.fields.MsgspecSchemaField(
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        schema=django_msgspec_field.compat.django.GenericContainer(
                            typing.Union,
                            (
                                django_msgspec_field.compat.django.GenericContainer(
                                    list,
                                    (
                                        django_msgspec_field.compat.django.GenericContainer(
                                            typing_extensions.Literal, ("foo",)
                                        ),
                                    ),
                                ),
                                django_msgspec_field.compat.django.GenericContainer(
                                    typing_extensions.Literal, ("bar",)
                                ),
                            ),
                        ),
                    ),
                ),
            ],
        ),
    ]
