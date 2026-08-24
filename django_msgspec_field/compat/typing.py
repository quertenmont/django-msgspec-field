try:
    from typing import get_args
    from typing import get_origin
except ImportError:
    from typing import get_args  # type: ignore  # noqa: F401
    from typing import get_origin  # type: ignore  # noqa: F401

__all__ = ["get_args", "get_origin"]
