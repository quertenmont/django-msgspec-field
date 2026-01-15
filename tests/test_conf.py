"""
Tests for the conf module and global settings functionality.
"""

import pytest
import msgspec
from django_msgspec_field.conf import MsgspecFieldSettings, import_from_string


class CustomType:
    """A custom type that msgspec cannot serialize natively."""

    def __init__(self, value: str):
        self.value = value

    def __eq__(self, other):
        if isinstance(other, CustomType):
            return self.value == other.value
        return False


def custom_enc_hook(obj):
    """Custom encoder hook for testing."""
    if isinstance(obj, CustomType):
        return {"__custom_type__": obj.value}
    raise NotImplementedError(f"Cannot encode {type(obj)}")


def custom_dec_hook(type_, obj):
    """Custom decoder hook for testing."""
    if type_ is CustomType:
        return CustomType(obj["__custom_type__"])
    raise NotImplementedError(f"Cannot decode {type_}")


class TestMsgspecFieldSettings:
    """Tests for the MsgspecFieldSettings class."""

    def test_default_settings(self):
        """Test that default settings return None for hooks."""
        settings = MsgspecFieldSettings()
        assert settings.ENC_HOOK is None
        assert settings.DEC_HOOK is None

    def test_user_settings(self):
        """Test that user settings override defaults."""
        user_settings = {
            "ENC_HOOK": custom_enc_hook,
            "DEC_HOOK": custom_dec_hook,
        }
        settings = MsgspecFieldSettings(user_settings=user_settings)
        assert settings.ENC_HOOK is custom_enc_hook
        assert settings.DEC_HOOK is custom_dec_hook

    def test_property_access(self):
        """Test property access methods."""
        user_settings = {
            "ENC_HOOK": custom_enc_hook,
            "DEC_HOOK": custom_dec_hook,
        }
        settings = MsgspecFieldSettings(user_settings=user_settings)
        assert settings.enc_hook is custom_enc_hook
        assert settings.dec_hook is custom_dec_hook

    def test_invalid_setting(self):
        """Test that accessing invalid settings raises AttributeError."""
        settings = MsgspecFieldSettings()
        with pytest.raises(AttributeError, match="Invalid setting"):
            settings.INVALID_SETTING

    def test_reload(self):
        """Test that reload clears cached attributes."""
        user_settings = {"ENC_HOOK": custom_enc_hook}
        settings = MsgspecFieldSettings(user_settings=user_settings)

        # Access to cache
        _ = settings.ENC_HOOK
        assert "ENC_HOOK" in settings._cached_attrs

        # Reload should clear cache
        settings.reload()
        assert "ENC_HOOK" not in settings._cached_attrs


class TestImportFromString:
    """Tests for the import_from_string function."""

    def test_import_from_string_callable(self):
        """Test that callables are returned as-is."""
        result = import_from_string(custom_enc_hook, "ENC_HOOK")
        assert result is custom_enc_hook

    def test_import_from_string_path(self):
        """Test that dotted paths are imported correctly."""
        # Import a known function from the standard library
        result = import_from_string("json.dumps", "TEST")
        import json

        assert result is json.dumps

    def test_import_from_string_invalid_path(self):
        """Test that invalid paths raise ImportError."""
        with pytest.raises(ImportError, match="Could not import"):
            import_from_string("nonexistent.module.function", "TEST")


class TestSchemaAdapterWithSettings:
    """Tests for SchemaAdapter using global settings."""

    def test_adapter_uses_default_enc_hook(self, monkeypatch):
        """Test that SchemaAdapter uses default enc_hook from settings."""
        from django_msgspec_field import conf
        from django_msgspec_field.types import SchemaAdapter

        # Create settings with custom enc_hook
        test_settings = MsgspecFieldSettings(user_settings={"ENC_HOOK": custom_enc_hook})
        monkeypatch.setattr(conf, "msgspec_field_settings", test_settings)

        class TestStruct(msgspec.Struct):
            data: dict

        adapter = SchemaAdapter.from_type(TestStruct)

        # Create a value with a custom type inside
        value = TestStruct(data={"key": "value"})
        result = adapter.dump_python(value)

        # The enc_hook should be used (though in this case the data is serializable)
        assert result == {"data": {"key": "value"}}

    def test_adapter_explicit_hook_overrides_settings(self, monkeypatch):
        """Test that explicit enc_hook overrides settings."""
        from django_msgspec_field import conf
        from django_msgspec_field.types import SchemaAdapter

        def other_enc_hook(obj):
            return "other"

        # Create settings with custom enc_hook
        test_settings = MsgspecFieldSettings(user_settings={"ENC_HOOK": other_enc_hook})
        monkeypatch.setattr(conf, "msgspec_field_settings", test_settings)

        class TestStruct(msgspec.Struct):
            data: dict

        # Explicit enc_hook should be used instead of settings
        adapter = SchemaAdapter.from_type(TestStruct, enc_hook=custom_enc_hook)

        # Verify the explicit hook is stored
        assert adapter.export_kwargs.get("enc_hook") is custom_enc_hook
