"""
Django settings configuration for django-msgspec-field.

This module provides a Django-like settings interface for configuring
default behavior of msgspec fields.

Usage:
    Add these settings to your Django settings.py file:

    DJANGO_MSGSPEC_FIELD = {
        "ENC_HOOK": my_enc_hook_function,
        "DEC_HOOK": my_dec_hook_function,
    }

    # Or using a dotted path to a function:
    DJANGO_MSGSPEC_FIELD = {
        "ENC_HOOK": "myapp.hooks.my_enc_hook",
        "DEC_HOOK": "myapp.hooks.my_dec_hook",
    }
"""

from __future__ import annotations

import typing as ty
from functools import lru_cache

if ty.TYPE_CHECKING:
    from collections.abc import Callable

# Default settings
DEFAULTS: dict[str, ty.Any] = {
    "ENC_HOOK": None,
    "DEC_HOOK": None,
}

# Keys that are expected to be callables or dotted paths to callables
IMPORT_STRINGS: tuple[str, ...] = (
    "ENC_HOOK",
    "DEC_HOOK",
)


def import_from_string(value: str | ty.Any, setting_name: str) -> ty.Any:
    """
    Import a callable from a dotted path string.

    Args:
        value: Either a callable or a dotted path string to import.
        setting_name: The name of the setting (for error messages).

    Returns:
        The imported callable, or the original value if not a string.
    """
    if isinstance(value, str):
        try:
            from django.utils.module_loading import import_string

            return import_string(value)
        except ImportError as e:
            raise ImportError(
                f"Could not import '{value}' for setting '{setting_name}'. {e.__class__.__name__}: {e}."
            ) from e
    return value


class MsgspecFieldSettings:
    """
    A settings object that provides access to django-msgspec-field settings.

    Settings are accessed as attributes on this object, with defaults provided
    by the DEFAULTS dict above.
    """

    def __init__(
        self,
        user_settings: dict[str, ty.Any] | None = None,
        defaults: dict[str, ty.Any] | None = None,
        import_strings: tuple[str, ...] | None = None,
    ):
        self._user_settings = user_settings or {}
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs: set[str] = set()

    @property
    def user_settings(self) -> dict[str, ty.Any]:
        if not self._user_settings:
            self._user_settings = self._load_user_settings()
        return self._user_settings

    def _load_user_settings(self) -> dict[str, ty.Any]:
        """Load user settings from Django settings."""
        try:
            from django.conf import settings

            return getattr(settings, "DJANGO_MSGSPEC_FIELD", {})
        except Exception:
            return {}

    def __getattr__(self, attr: str) -> ty.Any:
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into callables
        if attr in self.import_strings:
            val = import_from_string(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self) -> None:
        """Reload settings from Django settings."""
        for attr in self._cached_attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass
        self._cached_attrs.clear()
        self._user_settings = {}

    @property
    def enc_hook(self) -> Callable[[ty.Any], ty.Any] | None:
        """Get the default encoder hook."""
        return self.ENC_HOOK

    @property
    def dec_hook(self) -> Callable[[type, ty.Any], ty.Any] | None:
        """Get the default decoder hook."""
        return self.DEC_HOOK


@lru_cache(maxsize=1)
def get_settings() -> MsgspecFieldSettings:
    """Get the msgspec field settings singleton."""
    return MsgspecFieldSettings()


# Expose a module-level settings object for convenient access
msgspec_field_settings = get_settings()


def reload_settings() -> None:
    """Reload the settings from Django configuration."""
    get_settings.cache_clear()
    global msgspec_field_settings
    msgspec_field_settings = get_settings()
