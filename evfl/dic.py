import typing

from evfl.util import *

def _bit_mismatch(int1: int, int2: int) -> int:
    """Returns the index of the first different bit or -1 if the values are the same."""
    for i in range(max(int1.bit_length(), int2.bit_length())):
        if (int1 >> i) & 1 != (int2 >> i) & 1:
            return i
    return -1

def _first_1bit(n: int) -> int:
    for i in range(n.bit_length()):
        if (n >> i) & 1:
            return i
    assert False

def _bit(n: int, b: int) -> int:
    return (n >> (b & 0xffffffff)) & 1

class IndexTableEntry(typing.NamedTuple):
    name: str
    compact_bit_idx: int
    idx0: int
    idx1: int

    def __str__(self) -> str:
        return f'[{self.compact_bit_idx}] {self.name}'

def debug_print_graph(table: typing.List[IndexTableEntry]) -> None:
    print('digraph {')
    for d in table:
        print(f'"{d}" -> "{table[d.idx0]}" [color=red];')
        print(f'"{d}" -> "{table[d.idx1]}" [color=green];')
    print('}')

class _Node:
    __slots__ = ['child', 'data', 'bit_idx', 'parent']
    def __init__(self, data: int, bit_idx: int, parent) -> None:
        self.child: typing.List[_Node] = [self, self]
        self.data = data
        self.bit_idx = bit_idx
        # Trade space complexity for convenience.
        self.parent = parent

    def __str__(self) -> str:
        if self.data == 0:
            return '<ROOT>'
        return f'[{self.bit_idx}] {self.get_name()}'

    def get_name(self) -> str:
        return self.data.to_bytes((self.data.bit_length() + 7) // 8, byteorder='big').decode()

    def get_compact_bit_idx(self) -> int:
        byte_idx = self.bit_idx // 8
        return (byte_idx << 3) | (self.bit_idx - 8*byte_idx)

class Tree(_Node):
    """Implementation of a binary radix search tree used by Nintendo's DIC data structure.

    It is not intended to be used for lookups (as such, it does _not_ store any data)
    but only to build a DIC and in particular to generate the index table."""

    __slots__ = ['_entries']
    def __init__(self) -> None:
        super().__init__(0, -1, self)
        self._entries: typing.Dict[int, typing.Tuple[int, _Node]] = dict()
        self._insert_entry(0, self)

    def get_compact_bit_idx(self) -> int:
        return -1

    def search(self, data: int, prev: bool) -> _Node:
        if self.child[0] is self:
            return self
        node = self.child[0]
        prev_node = node
        while True:
            prev_node = node
            node = node.child[_bit(data, node.bit_idx)]
            if node.bit_idx <= prev_node.bit_idx:
                break
        return prev_node if prev else node

    def _insert_entry(self, data: int, node: _Node) -> None:
        self._entries[data] = (len(self._entries), node)

    def insert(self, name: str) -> None:
        data = int.from_bytes(name.encode(), byteorder='big')

        current = self.search(data, prev=True)
        bit_idx = _bit_mismatch(current.data, data)
        while bit_idx < current.parent.bit_idx:
            current = current.parent

        if bit_idx < current.bit_idx:
            # Insert before the current node as our bit index is lower,
            # which means the new node is closer to the root than the current one.
            new = _Node(data, bit_idx, current.parent)
            new.child[_bit(data, bit_idx)^1] = current
            current.parent.child[_bit(data, current.parent.bit_idx)] = new
            current.parent = new
            self._insert_entry(data, new)

        elif bit_idx > current.bit_idx:
            # Insert as a child of the current node as our bit index is higher,
            # which means the new node is deeper in the tree.
            new = _Node(data, bit_idx, current)
            if _bit(current.data, bit_idx) == _bit(data, bit_idx)^1:
                new.child[_bit(data, bit_idx)^1] = current
            else:
                new.child[_bit(data, bit_idx)^1] = self
            current.child[_bit(data, current.bit_idx)] = new
            self._insert_entry(data, new)

        else:
            # Both nodes have the same depth: insert the new node as a child of the current node.
            # Preserve tree invariants (bit indices must increase during traversal)
            # by using a higher bit index.
            # Nintendo's algorithm seems to use the index of the first set bit.
            new_bit_idx = _first_1bit(data)
            # If the current node pointed to another node, use the bit that differentiates
            # the new node from the other one.
            if current.child[_bit(data, bit_idx)] != self:
                new_bit_idx = _bit_mismatch(current.child[_bit(data, bit_idx)].data, data)
            new = _Node(data, new_bit_idx, current)
            new.child[_bit(data, new_bit_idx)^1] = current.child[_bit(data, bit_idx)]
            current.child[_bit(data, bit_idx)] = new
            self._insert_entry(data, new)

    def get_index_table(self) -> typing.List[IndexTableEntry]:
        return [IndexTableEntry(node.get_name(), node.get_compact_bit_idx(),
                                self._entries[node.child[0].data][0], self._entries[node.child[1].data][0])
                for idx, node in self._entries.values()]

class DicWriter(BinaryObject):
    __slots__ = ['_tree']
    def __init__(self) -> None:
        super().__init__()
        self._tree = Tree()

    def insert(self, key: str) -> None:
        self._tree.insert(key)

    def _do_read(self, stream: ReadStream) -> None:
        raise NotImplementedError()

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(b'DIC ')
        index_table = self._tree.get_index_table()
        stream.write(u32(len(index_table) - 1))
        for entry in index_table:
            stream.write(u32(entry.compact_bit_idx & 0xffffffff))
            stream.write(u16(entry.idx0))
            stream.write(u16(entry.idx1))
            stream.write_string_ref(entry.name)

class DicReader(BinaryObject):
    __slots__ = ['items']
    def __init__(self) -> None:
        super().__init__()
        self.items: typing.List[str] = []

    def _do_read(self, stream: ReadStream) -> None:
        magic = stream.read_u32()
        num_entries = stream.read_u32()
        stream.skip(4 + 2 + 2 + 8) # Root entry
        for i in range(num_entries):
            stream.skip(4 + 2 + 2)
            self.items.append(stream.read_string_ref())
            assert self.items[-1], 'Invalid entry name'

    def _do_write(self, stream: WriteStream) -> None:
        raise NotImplementedError()
