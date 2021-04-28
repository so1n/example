import logging
from typing import Any

from .g import g  # type: ignore


class RequestIDLogFilter(logging.Filter):
    """
    Log filter to inject the current request id of the request under `log_record.request_id`
    """

    def filter(self, record: Any) -> Any:
        record.request_id = g.request_id or None
        return record
