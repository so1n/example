from typing import Any, List, Optional, Tuple


class CustomerDict(object):

    def __init__(self):
        self._init_seed: int = 3  # 容量因子
        self._init_length: int = 2 ** self._init_seed  # 初始化数组大小
        self._load_factor: float = 2 / 3  # 扩容因子
        self._index_array: List[int] = [-1 for _ in range(self._init_length)]  # 存放下标的数组
        self._data_array: List[Optional[Tuple[int, Any, Any]]] = []  # 存放数据的数组
        self._used: int = 0  # 目前用的量

    def _create_new(self):
        """扩容函数"""
        self._init_seed += 1  # 增加容量因子
        self._init_length = 2 ** self._init_seed
        old_data_array: List[Tuple[int, Any, Any]] = self._data_array
        self._index_array: List[int] = [-1 for _ in range(self._init_length)]
        self._data_array: List[Tuple[int, Any, Any]] = []
        self._used = 0

        # 这里只是简单实现, 实际上只需要搬运一半的数据
        for item in old_data_array:
            if item is not None:
                self.__setitem__(item[1], item[2])

    def _get_next(self, index: int):
        """如果下标对应的值冲突了, 需要计算下一跳的下标"""
        return ((5*index) + 1) % self._init_length

    def __getitem__(self, key: Any) -> Any:
        index: int = hash(key) % (self._init_length - 1)
        while True:
            data_index: int = self._index_array[index]
            # 如果是-1则代表没有数据
            if data_index == -1:
                raise KeyError(key)
            # 如果是-2则代表之前有数据则不过被删除了
            elif data_index == -2:
                index = self._get_next(index)
                continue

            _, new_key, value = self._data_array[data_index]
            if key != new_key:
                index = self._get_next(index)
            else:
                return value

    def __setitem__(self, key: Any, value: Any) -> None:
        index: int = hash(key) % (self._init_length - 1)
        if (self._used / self._init_length) > self._load_factor:
            self._create_new()
        while True:
            data_index: int = self._index_array[index]
            if data_index == -1:
                break
            elif data_index == -2:
                index = self._get_next(index)
                continue
            _, new_key, _ = self._data_array[data_index]
            if key != new_key:
                index = self._get_next(index)
            else:
                break

        self._index_array[index] = self._used
        self._data_array.append((hash(key), key, value))
        self._used += 1

    def __delitem__(self, key: Any) -> None:
        index: int = hash(key) % (self._init_length - 1)
        while True:
            data_index: int = self._index_array[index]
            if data_index == -1:
                raise KeyError(key)
            elif data_index == -2:
                index = self._get_next(index)
                continue

            _, new_key, _ = self._data_array[data_index]
            if key != new_key:
                index = self._get_next(index)
            else:
                break
        self._index_array[index] = -2
        self._data_array[data_index] = None
    
    def __str__(self) -> str:
        return str({item[1]: item[2] for item in self._data_array if item is not None})


if __name__ == '__main__':
    customer_dict: CustomerDict = CustomerDict()
    customer_dict["demo_1"] = "a"
    customer_dict["demo_2"] = "b"
    print(customer_dict)
    del customer_dict["demo_1"]
    del customer_dict["demo_2"]
    print(customer_dict)
    for i in range(30):
        customer_dict[i] = i
    print(customer_dict)
    for i in range(30):
        assert customer_dict[i] == i
        del customer_dict[i]
