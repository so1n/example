from flask import Response, current_app, make_response
from werkzeug.exceptions import HTTPException


def api_exception(exc: Exception) -> Response:
    if isinstance(exc, HTTPException):
        # Flask自己的http错误
        resp = make_response(exc.description, exc.code)
        return resp
    else:
        current_app.logger.exception(exc)
        return make_response(exc)
