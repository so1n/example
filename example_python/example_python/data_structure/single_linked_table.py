from typing import Any, Optional


class Node(object):
    """创建数据和数据对应的指针"""
    def __init__(self, val: Any, node: Optional["Node"] = None):
        self.data: Any = val
        self.next: Optional["Node"] = node


class LinkList(object):
    def __init__(self):
        self.head: Optional[Node] = None
        self.length: int = 0

    @classmethod
    def from_list(cls, raw_list: list) -> "LinkList":
        """通过list写入数据"""
        instance: "LinkList" = cls()
        instance.head = Node(raw_list[0])
        node: Node = instance.head

        for i in raw_list[1:]:
            new_node: Node = Node(i)
            # 定义指针
            node.next = new_node
            # 定义下一个数
            node = new_node
        instance.length = len(raw_list)
        return instance

    def to_list(self, left: int = 0, right: int = -1) -> list:
        """获取列表的函数，如果没输入right时，则默认读取到最后面，如果没输入left和right则输出全部数据.left不能大于等于right"""
        if self.is_empty():
            raise ValueError('Linklist is empty.')
        cursor: int = 0
        node: Node = self.head
        if right == -1:
            right = self.length
        if right > self.length or left >= right:
            raise ValueError('right param error')

        while node.next and cursor < left:
            node = node.next
            cursor += 1
        new_list: list = []
        while node and cursor <= right:
            new_list.append(node.data)
            cursor += 1
            node = node.next
        return new_list

    def __len__(self):
        return self.length

    def is_empty(self) -> bool:
        return self.length == 0

    def clear(self):
        self.head = None
        self.length = 0

    def append(self, item: Any):
        # 在列表最后面添加一个数据
        new_node: Node = Node(item)
        if not self.head:
            self.head = new_node
        else:
            node: Node = self.head
            while node.next:
                node = node.next
            node.next = new_node

    def __getitem__(self, index: int) -> Any:
        self._check_index(index)

        cursor: int = 0
        node: Node = self.head

        while node:
            node = node.next
            cursor += 1
            if cursor == index:
                return node.data

        raise ValueError('target is not exist!')

    def _check_index(self, index: int):
        if self.is_empty() or index < 0 or index > self.length:
            raise ValueError(f"index:{index} error")

    def __setitem__(self, index: int, item: Any):
        """单独实现替换, 节省一遍查询"""
        self._check_index(index)

        node: Node = self.head
        if index == 0:
            new_node: Node = node.next
            self.head = new_node
        elif index == self.length - 1:
            self.append(item)
        else:
            cursor: int = 0
            while node:
                prev_node = node
                node = node.next
                cursor += 1

                if index == cursor:
                    new_node = Node(item, node.next)
                    prev_node.next = new_node

    def insert(self, index: int, item: Any):
        """向指定位置插入数据"""
        self._check_index(index)

        if index == 0:
            new_node: Node = Node(item, self.head)
            self.head = new_node
        elif index == self.length - 1:
            self.append(item)
        else:
            node: Node = self.head
            cursor: int = 0
            while node:
                prev_node = node
                node = node.next
                cursor += 1

                if index == cursor:
                    new_node = Node(item, node)
                    prev_node.next = new_node
                    new_node.next = node

    def delete(self, index: int):
        """删除指定位置数据"""
        self._check_index(index)

        node: Node = self.head
        # 如果是0的话，起点改为第二个数据
        if index == 0:
            new_node: Node = node.next
            self.head = new_node
        else:
            cursor: int = 1
            while node:
                prev_node = node
                node = node.next
                cursor += 1
                # 把下一个数据的指针，改为下下个数据的指针
                if index == cursor:
                    prev_node.next = node.next

    def __contains__(self, item: Any) -> bool:
        """查找元素是否在里面"""
        if self.is_empty():
            raise ValueError('Linklist is empty.')

        node: Node = self.head
        while node:
            if item == node.data:
                return True
            node = node.next
        return False


if __name__ == "__main__":
    link_list: LinkList = LinkList.from_list(["a", "b", "c", "d"])
    link_list.append("e")
    print(link_list.to_list())
    print("e" in link_list)
    link_list.delete(4)
    print(link_list.to_list())
    print(link_list[2])
    link_list[2] = "z"
    print(link_list[2])
    print(link_list.to_list())
