from queue import Queue
from typing import Any, Optional


class BinaryTreeNode(object):
    def __init__(self, data: Any, left: Optional["BinaryTreeNode"] = None, right: Optional["BinaryTreeNode"] = None):
        self.left: Optional["BinaryTreeNode"] = left
        self.right: Optional["BinaryTreeNode"] = right
        self.data: Any = data


class BinaryTreeHelper(object):
    def __init__(self, root: BinaryTreeNode):
        self.root: BinaryTreeNode = root

    def pre_order(self, node: Optional[BinaryTreeNode] = None) -> list:
        """前序遍历"""
        if node is None:
            node = self.root
        _list: list = []

        if node is not None:
            _list.append(node.data)
            if node.left is not None:
                _list.extend(self.pre_order(node.left))
            if node.right is not None:
                _list.extend(self.pre_order(node.right))
        return _list

    def in_order(self, node: Optional[BinaryTreeNode] = None) -> list:
        """中序遍历"""
        if node is None:
            node = self.root
        _list: list = []
        if node is not None:
            if node.left is not None:
                _list.extend(self.in_order(node.left))
            _list.append(node.data)
            if node.right is not None:
                _list.extend(self.in_order(node.right))
        return _list

    def post_order(self, node: Optional[BinaryTreeNode] = None) -> list:
        """后序遍历"""
        if node is None:
            node = self.root
        _list: list = []
        if node is not None:
            if node.left is not None:
                _list.extend(self.post_order(node.left))
            if node.right is not None:
                _list.extend(self.post_order(node.right))
            _list.append(node.data)
        return _list

    def level_order(self, node: Optional[BinaryTreeNode] = None) -> list:
        """层级遍历"""
        if node is None:
            node = self.root
        _list: list = []

        queue: "Queue" = Queue()
        while node is not None:
            _list.append(node.data)
            if node.left is not None:
                queue.put(node.left)
            if node.right is not None:
                queue.put(node.right)
            if queue.empty():
                node = None
            else:
                node = queue.get()
        return _list


if __name__ == "__main__":
    binary_tree: BinaryTreeNode = BinaryTreeNode(
        "0",
        BinaryTreeNode(
            "1",
            BinaryTreeNode(
                "3",
                BinaryTreeNode("7"),
                BinaryTreeNode("8")
            ),
            BinaryTreeNode(
                "4",
                BinaryTreeNode("9")
            )
        ),
        BinaryTreeNode(
            "2",
            BinaryTreeNode("5"),
            BinaryTreeNode("6"),
        )
    )
    binary_tree_helper: BinaryTreeHelper = BinaryTreeHelper(binary_tree)
    print("层级遍历", binary_tree_helper.level_order())
    print("前序遍历", binary_tree_helper.pre_order())
    print("中序遍历", binary_tree_helper.in_order())
    print("后序遍历", binary_tree_helper.post_order())



