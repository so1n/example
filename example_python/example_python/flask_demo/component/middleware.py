import time
from typing import Union
from uuid import uuid4

from flask import Blueprint, Flask, Response, current_app, g, request

from .g import g

APP_TYPE = Union[Blueprint, Flask]


class BaseMiddleware(object):
    def __init__(self, app: APP_TYPE) -> None:
        self._app = app
        self._app.before_request(self._before_requests)
        self._app.after_request(self._after_requests)

    def _before_requests(self) -> None:
        raise NotImplementedError

    def _after_requests(self, response: Response) -> Response:
        return response


class AccessMiddleware(BaseMiddleware):
    def _before_requests(self) -> None:
        g.start_time = time.time()
        g.request_id = request.headers.get("X-Request-Id", str(uuid4()))

    def _after_requests(self, response: Response) -> Response:
        code: int = -1
        msg: str = ""

        if response.is_json:
            code = response.json.get("code", -1)
            msg = response.json.get("msg", "")
        current_app.logger.info(
            f"[{request.method}]{request.path} status:{response.status_code} api_code:{code} msg:{msg or 'success'}"
            f' duration:{time.time() - g.start_time} ip:{request.headers.get("X-Real-Ip", request.remote_addr)}'
        )
        return response
