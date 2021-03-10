from typing import Any, Optional


class Node(object):
    """创建数据和数据对应的指针"""
    def __init__(self, val: Any, next_node: Optional["Node"] = None, prev_node: Optional["Node"] = None):
        self.data: Any = val
        self.next: Optional["Node"] = next_node
        self.prev: Optional["None"] = prev_node


class Deque(object):
    def __init__(self, max_length: int):
        # 定义队列长度
        self.size: int = 0
        self.max_length: int = max_length

        # 定义首尾node
        self.head_node: Optional[Node] = None
        self.tail_node: Optional[Node] = None

    def put_left(self, value: Any):
        if self.is_full():
            raise Exception("queue is full")
        elif self.is_empty():
            node: Node = Node(value)
            self.head_node = node
            self.tail_node = node
        else:
            node: Node = Node(value, self.head_node, self.tail_node)
            self.tail_node.next = node
            self.head_node = node
        self.size += 1

    def put(self, value: Any):
        """入队操作"""
        if self.is_full():
            raise Exception("queue is full")
        elif self.is_empty():
            node: Node = Node(value)
            self.head_node = node
            self.tail_node = node
        else:
            node: Node = Node(value, self.head_node, self.tail_node)
            self.tail_node.next = node
            self.tail_node = node
        self.size += 1

    def get(self) -> Any:
        # 出队操作，切片取数据是O(1)，如果要使用remove复杂度为O(k)
        if self.is_empty():
            raise Exception("queue is empty")
        else:
            self.size -= 1
            value: Any = self.head_node.data
            self.head_node = self.head_node.next
            return value

    def pop(self) -> Any:
        if self.is_empty():
            raise Exception("queue is empty")
        else:
            self.size -= 1
            value: Any = self.tail_node.data
            self.tail_node = self.tail_node.prev
            self.tail_node.next = self.head_node
            self.head_node.prev = self.tail_node
            return value

    def __len__(self) -> int:
        if self.is_empty():
            raise Exception("queue is empty")
        return self.size

    def is_full(self) -> bool:
        return self.size == self.max_length

    def is_empty(self) -> bool:
        return self.size == 0

    @classmethod
    def from_list(cls, raw_list: list) -> "Deque":
        instance: "Deque" = cls(len(raw_list))
        for i in raw_list:
            instance.put(i)
        return instance

    def to_list(self) -> list:
        if self.is_empty():
            raise Exception("queue is empty")
        _list: list = []
        node: Node = self.head_node
        while node:
            _list.append(node.data)
            if node.next is self.head_node:
                break
            node = node.next
        return _list


if __name__ == "__main__":
    queue: Deque = Deque.from_list(["a", "b", "c", "d"])
    print(queue.to_list())
    print(queue.get())
    queue.put("e")
    print(queue.to_list())
    queue.pop()
    queue.put_left("a")
    print(queue.to_list())
    while not queue.is_empty():
        print(queue.get())
