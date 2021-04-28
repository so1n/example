from typing import Any

from flask import g as _g


class Helper(object):
    def __init__(self, key: str):
        self.key: str = "_helper_" + key

    def __get__(self, instance: Any, owner: Any) -> Any:
        return getattr(_g, self.key, None)

    def __set__(self, instance: Any, value: Any) -> Any:
        setattr(_g, self.key, value)


class _G(object):
    request_id: str = Helper("request_id")  # type: ignore


g: "_G" = _G()
