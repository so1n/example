import time
import sys

from typing import Callable, NoReturn


class Tail(object):
    def __init__(
            self,
            file_name: str,
            output: Callable[[str], NoReturn] = sys.stdout.write,
            interval: int = 1
    ):
        self.file_name: str = file_name
        self.output: Callable[[str], NoReturn] = output
        self.interval: int = interval

    def __call__(self):
        with open(self.file_name) as f:
            f.seek(0, 2)  # 从文件结尾处开始seek
            while True:
                line: str = f.readline()
                if line:
                    self.output(line)  # 使用print都会每次都打印新的一行
                else:
                    time.sleep(self.interval)


if __name__ == '__main__':
    filename: str = sys.argv[0]
    Tail(filename)()
