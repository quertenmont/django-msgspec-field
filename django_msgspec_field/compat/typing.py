try:
    from typing import get_args as get_args
    from typing import get_origin as get_origin
except ImportError:
    from typing import get_args as get_args  # type: ignore
    from typing import get_origin as get_origin  # type: ignore
