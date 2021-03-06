import typing
import unittest

from evfl.dic import IndexTableEntry, Tree

entry_points = ['Always', 'Rejection', 'Before_FirstTouchdown', 'FirstTouchdown',
                'FindDungeon_Activated', 'FindDungeon_Finish', 'FindDungeon_1stClear',
                'IsPlayed_Demo103_0']

class TreeReachabilityTest(unittest.TestCase):
    """Tests whether all nodes in the tree are reachable."""
    def test(self) -> None:
        tree = Tree()

        for item in entry_points:
            tree.insert(item)

        for item in entry_points:
            data = int.from_bytes(item.encode(), 'big')
            self.assertEqual(tree.search(data, prev=False).data, data)

class TreeReachabilityStressTest(unittest.TestCase):
    """Tests whether all nodes in the tree are reachable with many more nodes."""
    def test(self) -> None:
        tree = Tree()

        for i in range(1000):
            tree.insert(f'Test{i}')
            tree.insert(f'Foo{i}Bar')
            tree.insert(f'{i}BarFoo')

        for i in range(1000):
            data = int.from_bytes(f'Test{i}'.encode(), 'big')
            self.assertEqual(tree.search(data, prev=False).data, data)

            data = int.from_bytes(f'Foo{i}Bar'.encode(), 'big')
            self.assertEqual(tree.search(data, prev=False).data, data)

            data = int.from_bytes(f'{i}BarFoo'.encode(), 'big')
            self.assertEqual(tree.search(data, prev=False).data, data)

def is_reachable_in_index_table(wanted: str, table: typing.List[IndexTableEntry]) -> bool:
    node_idx = table[0].idx0
    node = table[node_idx]
    if table[0].compact_bit_idx < node.compact_bit_idx:
        while True:
            next_idx = 0
            if len(wanted) > (node.compact_bit_idx >> 3):
                next_idx = (ord(wanted[len(wanted) +~(node.compact_bit_idx >> 3)]) >> (node.compact_bit_idx & 7)) & 1
            current_node = table[node_idx]
            node_idx = node.idx0 if next_idx == 0 else node.idx1
            node = table[node_idx]
            node_ref = node.compact_bit_idx
            if current_node.compact_bit_idx >= node.compact_bit_idx:
                break
    return node.name == wanted

class TreeIndexTableReachabilityStressTest(unittest.TestCase):
    """Tests whether all nodes in an index table are reachable with many more nodes."""
    def test(self) -> None:
        tree = Tree()

        for i in range(1000):
            tree.insert(f'Test{i}')
            tree.insert(f'Foo{i}Bar')
            tree.insert(f'{i}BarFoo')

        table = tree.get_index_table()
        for entry in table:
            self.assertTrue(is_reachable_in_index_table(entry.name, table))

class TreeIndexTableOrderTest(unittest.TestCase):
    """Tests whether the index table preserves insertion order."""
    def test(self) -> None:
        tree = Tree()

        items = ['A', 'C', 'B', 'Test']
        for item in items:
            tree.insert(item)

        table = tree.get_index_table()
        self.assertEqual(len(table) - 1, len(items))
        for item, entry in zip(items, table[1:]):
            self.assertTrue(is_reachable_in_index_table(entry.name, table))
            self.assertEqual(item, entry.name)

class TreeIdenticalToNintendo1Test(unittest.TestCase):
    """Tests whether a common tree is identical to the one generated by Nintendo."""
    def test(self) -> None:
        tree = Tree()

        expected_table = [
            IndexTableEntry(compact_bit_idx=-1, idx0=1, idx1=0, name=''),
            IndexTableEntry(compact_bit_idx=0, idx0=2, idx1=1, name='Always'),
            IndexTableEntry(compact_bit_idx=1, idx0=5, idx1=7, name='Rejection'),
            IndexTableEntry(compact_bit_idx=0xb, idx0=4, idx1=2, name='Before_FirstTouchdown'),
            IndexTableEntry(compact_bit_idx=0x70, idx0=4, idx1=3, name='FirstTouchdown'),
            IndexTableEntry(compact_bit_idx=2, idx0=6, idx1=5, name='FindDungeon_Activated'),
            IndexTableEntry(compact_bit_idx=3, idx0=8, idx1=6, name='FindDungeon_Finish'),
            IndexTableEntry(compact_bit_idx=2, idx0=7, idx1=3, name='FindDungeon_1stClear'),
            IndexTableEntry(compact_bit_idx=4, idx0=0, idx1=8, name='IsPlayed_Demo103_0'),
        ]

        for entry in expected_table[1:]:
            tree.insert(entry.name)

        table = tree.get_index_table()
        self.assertEqual(len(expected_table), len(table))
        for entry, expected_entry in zip(table, expected_table):
            self.assertEqual(entry, expected_entry)

class TreeIdenticalToNintendo2Test(unittest.TestCase):
    """Tests whether a common tree is identical to the one generated by Nintendo."""
    def test(self) -> None:
        tree = Tree()

        expected_table = [
            IndexTableEntry(name='', compact_bit_idx=-1, idx0=1, idx1=0),
            IndexTableEntry(name='CreateMode', compact_bit_idx=0, idx0=6, idx1=2),
            IndexTableEntry(name='IsGrounding', compact_bit_idx=1, idx0=5, idx1=2),
            IndexTableEntry(name='IsWorld', compact_bit_idx=2, idx0=4, idx1=3),
            IndexTableEntry(name='PosX', compact_bit_idx=3, idx0=0, idx1=7),
            IndexTableEntry(name='PosY', compact_bit_idx=2, idx0=8, idx1=1),
            IndexTableEntry(name='PosZ', compact_bit_idx=1, idx0=3, idx1=9),
            IndexTableEntry(name='RotX', compact_bit_idx=8, idx0=7, idx1=4),
            IndexTableEntry(name='RotY', compact_bit_idx=8, idx0=8, idx1=5),
            IndexTableEntry(name='RotZ', compact_bit_idx=8, idx0=9, idx1=6),
        ]

        for entry in expected_table[1:]:
            tree.insert(entry.name)

        table = tree.get_index_table()
        self.assertEqual(len(expected_table), len(table))
        for entry, expected_entry in zip(table, expected_table):
            self.assertEqual(entry, expected_entry)
