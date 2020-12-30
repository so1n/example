import time
import sys

from typing import Callable, List, NoReturn


class Tail(object):
    def __init__(
            self,
            file_name: str,
            output: Callable[[str], NoReturn] = sys.stdout.write,
            interval: int = 1,
            len_line: int = 1024
    ):
        self.file_name: str = file_name
        self.output: Callable[[str], NoReturn] = output
        self.interval: int = interval
        self.len_line: int = len_line

    def __call__(self, n: int = 10):
        with open(self.file_name) as f:
            self.read_last_line(f, n)
            while True:
                line: str = f.readline()
                if line:
                    self.output(line)  # 使用print都会每次都打印新的一行
                else:
                    time.sleep(self.interval)

    def read_last_line(self, file, n):
        read_len: int = self.len_line * n

        # 获取当前结尾的游标位置
        file.seek(0, 2)
        now_tell: int = file.tell()
        while True:
            if read_len > file.tell():
                # 如果跳转的字符长度大于原来文件长度,那就把所有文件内容打印出来
                file.seek(0)
                last_line_list: List[str] = file.read().split('\n')[-n:]
                # 重新获取游标位置
                now_tell: int = file.tell()
                break
            file.seek(-read_len, 2)
            read_str: str = file.read(read_len)
            cnt: int = read_str.count('\n')
            if cnt >= n:
                # 如果获取的行数大于要求的行数,则获取前n行的行数
                last_line_list: List[str] = read_str.split('\n')[-n:]
                break
            else:
                # 如果获取的行数小于要求的行数,则预估需要获取的行数,继续获取
                if cnt == 0:
                    line_per: int = read_len
                else:
                    line_per: int = int(read_len / cnt)
                read_len = line_per * n

        for line in last_line_list:
            self.output(line + '\n')
        # 重置游标,确保接下来打印的数据不重复
        file.seek(now_tell)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename")
    parser.add_argument("-n", "--num", default=10)
    args, unknown = parser.parse_known_args()
    if not args.filename:
        raise RuntimeError('filename args error')
    Tail(args.filename)(int(args.num))
