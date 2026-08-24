try:
    from typing import get_args, get_origin
except ImportError:
    from typing import (
        get_args,  # type: ignore
        get_origin,  # type: ignore
    )

__all__ = ["get_args", "get_origin"]
