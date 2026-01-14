"""
CoreAPI schema generation for msgspec schemas (legacy support).
"""

from __future__ import annotations

import importlib.util

# CoreAPI is deprecated in favor of OpenAPI, but we provide basic support
# for backwards compatibility.

try:
    if importlib.util.find_spec("coreapi") is None:
        raise ImportError

    from rest_framework.schemas import coreapi as drf_coreapi

    class AutoSchema(drf_coreapi.AutoSchema):
        """Legacy CoreAPI AutoSchema with msgspec support."""

        pass

except ImportError:
    # CoreAPI not installed
    class AutoSchema:  # type: ignore
        """Placeholder when CoreAPI is not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError("CoreAPI is not installed. Please install it with: pip install coreapi")
