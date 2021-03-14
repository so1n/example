# Twitter元年时间戳
TWEPOCH = 1288834974657


class InvalidSystemClock(Exception):
    pass


class SnowflakeWorker(object):

    def __init__(self, area_id: int, worker_id: int, sequence: int = 0, area_id_bit: int = 3) -> None:
        # 区域id与服务器id的计算
        worker_id_bit: int = 10 - area_id_bit
        max_worker_id: int = -1 ^ (-1 << worker_id_bit)
        max_area_id: int = -1 ^ (-1 << area_id_bit)

        # 计算偏移量
        self.sequence_bit: int = 12
        self.worker_id_shift: int = self.sequence_bit
        self.main_id_shift: int = self.sequence_bit + worker_id_bit
        self.timestamp_shift: int = self.sequence_bit + worker_id_bit + worker_id_bit

        # 序号循环掩码
        self.sequence_mask: int = -1 ^ (-1 < self.sequence_bit)

        if worker_id > max_worker_id or worker_id < 0:
            raise ValueError(f"work id bit must between 0 and {max_worker_id}")

        if area_id > max_area_id or area_id_bit < 0:
            raise ValueError(f"area id bit must between 0 and {max}")

        self.area_id: int = area_id
        self.worker_id: int = worker_id
        self.sequence: int = sequence

        self.last_timestamp: int = -1  # 上次计算的时间戳
        self._diff_timestamp: int = 0  # 出现时间回拨时的差值

    def _gen_millisecond_timestamp(self) -> int:
        """获取当前时间的timestamp, 13位"""
        return int(time.time() * 1000) + self._diff_timestamp

    def get_id(self):
        timestamp: int = self._gen_millisecond_timestamp()

        # 出现时间回拨, 借用未来时间
        if timestamp < self.last_timestamp:
            self._diff_timestamp = self._diff_timestamp + (self.last_timestamp - timestamp)
            timestamp = self.last_timestamp

        # 如果是同一个时间内获取, 则使用序列号
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            if self.sequence == 0:
                timestamp = self._get_next_millis(self.last_timestamp)
        else:
            self.sequence = 0

        self.last_timestamp = timestamp

        return ((timestamp - TWEPOCH) << self.timestamp_shift) | (self.area_id << self.main_id_shift) | \
               (self.worker_id << self.worker_id_shift) | self.sequence

    def _get_next_millis(self, last_timestamp):
        timestamp = self._gen_millisecond_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._gen_millisecond_timestamp()
        return timestamp


if __name__ == '__main__':
    i = 0
    import time
    while i < 3:
        worker = SnowflakeWorker(1, 2, 0)
        print(worker.get_id())
        time.sleep(1)
        i += 1
