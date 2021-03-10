from typing import Any


class LinearTable(object):
    """在Python中使用list模拟线性表..."""

    def __init__(self, max_length: int = 10, extend_num: int = 8):
        self.max_length: int = max_length

        # 当前有效的数组最长值
        # 比如数组实际长度为20, 当只用了10个, 那么num为10
        self.num: int = 0
        # 扩容的长度
        self.extend_num: int = extend_num
        self.data = [None] * self.max_length

    def is_empty(self) -> bool:
        return self.num == 0

    def is_full(self) -> bool:
        return self.num == self.max_length

    @classmethod
    def from_list(cls, raw_list: list):
        instance: "LinearTable" = cls()
        for i in raw_list:
            instance.append(i)
        return instance

    def to_list(self) -> list:
        return self.data[: self.num]

    def _extend(self):
        self.data.extend([None] * self.extend_num)

    def __getitem__(self, index: int) -> Any:
        if not isinstance(index, int):
            raise TypeError
        if 0 <= index < self.num:
            return self.data[index]
        else:
            # 表为空或者索引超出范围都会引发索引错误
            raise IndexError

    def __setitem__(self, index: int, value: Any):
        if not isinstance(index, int):
            raise TypeError
        # 只能访问列表里已有的元素,self.num=0时，一个都不能访问,self.num=1时，只能访问0
        if 0 <= index < self.num:
            self.data[index] = value
        else:
            raise IndexError

    def clear(self):
        self.__init__()

    def __len__(self):
        return self.num

    # 加入元素的方法 append()和insert()
    def append(self, value: Any):
        if self.is_full():
            # 如果满了则进行扩容
            self._extend()
        self.data[self.num] = value
        self.num += 1

    def insert(self, index: int, value: Any):
        if not isinstance(index, int):
            raise TypeError
        if index < 0:  # 暂时不考虑负数索引
            raise IndexError
        # 当key大于元素个数时，默认尾部插入
        if index > self.num:
            self.append(value)
        else:
            if self.is_full():
                self._extend()
            self.num += 1

            # 移动key后的元素
            for i in range(self.num, index, -1):
                self.data[i] = self.data[i - 1]
            # 赋值
            self.data[index] = value

    def remove(self, index: int = -1):
        """假删除, 只是把值往前挪, 缩小一个有效范围"""
        if not isinstance(index, int):
            raise TypeError
        if self.num - 1 < 0:
            raise IndexError("pop from empty list")
        elif index == -1:
            # 原来的数还在，但列表不识别他
            self.num -= 1
        else:
            for i in range(index, self.num - 1):
                self.data[i] = self.data[i + 1]
            self.num -= 1

    def index(self, value: Any, start: int = 0) -> int:
        """从第几个开始找, 找到则返回索引"""
        for i in range(start, self.num):
            if self.data[i] == value:
                return i
        # 没找到
        raise ValueError("%d is not in the list" % value)

    def reverse(self):
        """列表反转"""
        i, j = 0, self.num - 1
        while i < j:
            self.data[i], self.data[j] = self.data[j], self.data[i]
            i, j = i + 1, j - 1


if __name__ == "__main__":
    liner_table: LinearTable = LinearTable.from_list(["a", "b", "c", "d"])
    print(liner_table.to_list())
    liner_table.append("z")
    print(liner_table.to_list())
    liner_table.remove(liner_table.index("z"))
    liner_table.reverse()
    print(liner_table.to_list())
