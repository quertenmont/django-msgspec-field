import typing as t
from datetime import date

import msgspec
import pytest
from django.conf import settings
from rest_framework.test import APIRequestFactory
from syrupy.extensions.json import JSONSnapshotExtension


class InnerSchema(msgspec.Struct):
    """Test schema for inner data."""

    stub_str: str
    stub_list: t.List[date]
    stub_int: int = 1


class SampleDataclass(msgspec.Struct):
    """Test dataclass-like struct."""

    stub_str: str
    stub_list: t.List[date]
    stub_int: int = 1


class SchemaWithCustomTypes(msgspec.Struct):
    """Test schema with custom types."""

    url: str = "http://localhost/"
    uid: str = "367388a6-9b3b-4ef0-af84-a27d61a05bc7"


@pytest.fixture
def request_factory():
    return APIRequestFactory()


# ==============================
# PARAMETRIZED DATABASE BACKENDS
# ==============================


def sqlite_backend(settings):
    settings.CURRENT_TEST_DB = "default"


def postgres_backend(settings):
    settings.CURRENT_TEST_DB = "postgres"


def mysql_backend(settings):
    settings.CURRENT_TEST_DB = "mysql"


@pytest.fixture(
    params=[
        sqlite_backend,
        pytest.param(
            postgres_backend,
            marks=pytest.mark.skipif(
                "postgres" not in settings.DATABASES,
                reason="POSTGRES_DSN is not specified",
            ),
        ),
        pytest.param(
            mysql_backend,
            marks=pytest.mark.skipif(
                "mysql" not in settings.DATABASES,
                reason="MYSQL_DSN is not specified",
            ),
        ),
    ]
)
def available_database_backends(request, settings):
    yield request.param(settings)


@pytest.fixture
def snapshot_json(snapshot):
    return snapshot.use_extension(JSONSnapshotExtension)
