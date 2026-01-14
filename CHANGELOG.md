# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-14

### Added
- Initial release of django-msgspec-field
- Fork from django-pydantic-field, replacing Pydantic with msgspec
- `SchemaField` for Django models with msgspec validation
- Django Forms support with `SchemaField`
- Django REST Framework integration:
  - `SchemaField` for serializers
  - `SchemaParser` and `SchemaRenderer` for typed request/response handling
  - `AutoSchema` for OpenAPI schema generation
- Support for msgspec types: `Struct`, dataclasses, `TypedDict`, and standard Python types
- Migration serializers for Django migrations
- `django-jsonform` widget integration
- Full type hints support
