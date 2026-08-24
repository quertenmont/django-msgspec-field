"""
Backward compatibility module for migration serializers.
"""

import warnings

from .compat.django import *  # noqa: F403, F401

__all__ = [  # noqa: F405
    "AnnotatedAlias",
    "BaseContainer",
    "BaseContainerSerializer",
    "DataclassContainer",
    "DataclassContainerSerializer",
    "GenericContainer",
    "GenericTypes",
    "MsgspecMetaSerializer",
    "TypingSerializer",
    "UnionType",
    "UnionTypeSerializer",
]

DEPRECATION_MSG = (
    "Module 'django_msgspec_field._migration_serializers' is deprecated "
    "and will be removed in version 1.0.0. "
    "Please replace it with 'django_msgspec_field.compat.django' in migrations."
)
warnings.warn(DEPRECATION_MSG, category=DeprecationWarning)
