import logging
import contextvars
from contextlib import contextmanager
from functools import partial
from threading import Thread
from typing import Any, Callable, Dict, Generator, List, Optional, Type

from kombu import Connection, Consumer, Exchange, Message, Queue  # type: ignore
from kombu.mixins import ConsumerMixin  # type: ignore
from kombu.utils.encoding import safe_str  # type: ignore


# mq专用的线程上下文, 目前只针对req_id后续需要其他数据再拓展
mq_context: contextvars.ContextVar = contextvars.ContextVar("mq_context", default=None)


class SkipException(Exception):
    """解析函数才可以使用改异常, 主服务收到这个异常后会自动对消息进行ack"""
    pass


class ReqIDLogFilter(logging.Filter):
    """
    打印日志时, 带上的日志参数
    """

    def filter(self, record: Any) -> Any:
        record.req_id = mq_context.get()
        return record


# 初始化全局默认handler
default_handler: logging.Handler = logging.StreamHandler()
# 增加自定义的Filter
default_handler.addFilter(ReqIDLogFilter())
logging.basicConfig(
    format="[%(asctime)s][%(filename)s][line:%(lineno)d][%(levelname)s][%(req_id)s]%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[default_handler],
)
log: logging.Logger = logging.getLogger()


# 声明交换机
DEMO_EXCHANGE: Exchange = Exchange("DEMO_E", type="direct", delivery_mode=2)

# 声明队列
DEMO_QUEUE_LIST: List[Queue] = [Queue("DEMO_Q", DEMO_EXCHANGE, routing_key="demo_queue")]


def demo_parse_body(body_dict: Dict[str, Any]) -> None:
    try:
        1 / 0
    except ZeroDivisionError as e:
        raise SkipException from e
    except Exception:
        pass


class Worker(ConsumerMixin):
    """继承kombu的消费者类"""

    def __init__(
            self,
            worker_name: str,
            connection: Connection,
            interval_start: float = 2,
            interval_step: float = 2,
            interval_max: float = 30,
            msg_id_key: Optional[str] = None
    ) -> None:
        self.msg_id_key: Optional[str] = msg_id_key
        self.worker_name: str = worker_name
        self.connection: Connection = connection
        self._msg_title: str = f"mq listener worker:{worker_name} "
        self._interval_start: float = interval_start
        self._interval_step: float = interval_step
        self._interval_max: float = interval_max

    @contextmanager
    def establish_connection(self) -> Generator[Any, Any, None]:
        # 继承父类方法, 支持自定义连接重连间隔的参数
        with self.create_connection() as conn:
            conn.ensure_connection(
                self.on_connection_error,
                self.connect_max_retries,
                interval_start=self._interval_start,
                interval_step=self._interval_step,
                interval_max=self._interval_max
            )
            yield conn

    def on_connection_error(self, exc: Exception, interval: int) -> None:
        """连接出错时的报错, 这里可以接入报警系统"""
        super().on_connection_error(exc, interval)

    def on_decode_error(self, message: Message, exc: Exception) -> None:
        """编码错误时的报错, 会自动ack, 这里可以接入报警系统"""
        super().on_decode_error(message, exc)

    def on_msg_handle(self, callback: Callable[[Dict[str, Any]], None], body: Dict[str, Any], message: Message) -> None:
        """自定义的方法, 会自动预处理数据, 和报警, 如果是成功或者是skip错误, 就会自动ack"""
        consumer_name: str = callback.__name__
        tag: Optional[str] = None
        # 如果消息带有id,则直接使用消息的id
        if self.msg_id_key:
            tag = body.get(self.msg_id_key, None)

        if not tag:
            message_data_list = [
                message.delivery_info.get(key, None) for key in ["exchange", "routing_key", "delivery_tag"]
            ]
            tag = ".".join([i for i in message_data_list if i])
        log.info(f"{self.worker_name}:{consumer_name} recv msg, delivery info:{message.delivery_info} body:{body}")
        try:
            mq_context.set(f"{consumer_name}:{tag}")
            callback(body)
            message.ack()
        except SkipException as e:
            message.ack()
            log.info(f"recv skip error:{e} auto ack")
        except Exception as e:
            msg: str = f"{consumer_name} failed to handle recv msg, error: {e}"
            log.exception(msg)

    def get_consumers(self, consumer: Type[Consumer], channel: Exchange) -> List[Consumer]:
        # 模拟源代码的consumer生成
        consumer_list: List[Consumer] = [
            Consumer(
                queues=DEMO_QUEUE_LIST,
                accept=["json"],
                callbacks=[partial(self.on_msg_handle, demo_parse_body)],
                channel=channel,
                on_decode_error=self.on_decode_error,
            )
        ]
        for _consumer in consumer_list:
            log.info(f"worker:[{self.worker_name}] load consumer:{_consumer}")
        return consumer_list


if __name__ == "__main__":
    Worker("demo worker", Connection("amqp://user:password@ip:port//vhost")).run()
