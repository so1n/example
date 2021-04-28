
import logging
import logging.handlers
import pathlib

from flask import Flask
from flask.logging import default_handler

from component.exc import api_exception
from component.log_filtter import RequestIDLogFilter
from component.middleware import AccessMiddleware


def create_app() -> Flask:
    app: Flask = Flask("demo")
    app.config["PROJECT_PATH"] = str(pathlib.Path(__file__).parent.absolute())

    # 配置日志
    format_string: str = (
        "[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d:%(funcName)s:%(request_id)s]" " %(message)s"
    )
    default_handler.setFormatter(logging.Formatter(format_string))
    default_handler.addFilter(RequestIDLogFilter())

    # 加载中间件
    AccessMiddleware(app)

    # 路由函数有异常时,统一处理
    app.errorhandler(Exception)(api_exception)
    return app


flask_app: Flask = create_app()


if __name__ == "__main__":
    flask_app.run()
