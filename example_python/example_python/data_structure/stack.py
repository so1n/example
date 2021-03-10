from typing import Any


class Stack(object):
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
        instance: "Stack" = cls()
        for i in raw_list:
            instance.append(i)
        return instance

    def to_list(self) -> list:
        return self.data[: self.num]

    def _extend(self):
        self.data.extend([None] * self.extend_num)

    def __len__(self):
        return self.num

    def append(self, value: Any):
        if self.is_full():
            # 如果满了则进行扩容
            self._extend()
        self.data[self.num] = value
        self.num += 1

    def pop(self) -> Any:
        """假删除, 只是把值往前挪, 缩小一个有效范围"""
        if self.num - 1 < 0:
            raise IndexError("pop from empty list")
        else:
            value: Any = self.data[self.num]
            self.num -= 1
            return value


if __name__ == "__main__":
    stack: Stack = Stack.from_list(["a", "b", "c", "d"])
    stack.append("e")
    print(stack.to_list())
    stack.pop()
    print(stack.to_list())
