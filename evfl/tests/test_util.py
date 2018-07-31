import unittest

import evfl.util as util

sleep_str = 'Root/Timeline/Sleep/到着'
sleep_pascal_str_bytes = b'\x1A\x00\x52\x6F\x6F\x74\x2F\x54\x69\x6D\x65\x6C\x69\x6E\x65\x2F\x53\x6C\x65\x65\x70\x2F\xE5\x88\xB0\xE7\x9D\x80\x00'

class PascalStringUDecodeTest(unittest.TestCase):
    def test(self) -> None:
        string = util.read_pascal_string(b'\x05\x00Hello', 0)
        self.assertEqual(string, 'Hello')

        string = util.read_pascal_string(sleep_pascal_str_bytes, 0)
        self.assertEqual(string, 'Root/Timeline/Sleep/到着')

class PascalStringEncodeTest(unittest.TestCase):
    def test(self) -> None:
        data = util.pascal_string('Hello')
        self.assertEqual(data, b'\x05\x00Hello\x00')

        data = util.pascal_string(sleep_str)
        self.assertEqual(data, sleep_pascal_str_bytes)

        decoded_data = util.read_pascal_string(data, 0)
        self.assertEqual(decoded_data, sleep_str)

class ValueToIndexMapTest(unittest.TestCase):
    def test(self) -> None:
        data = {'test': 123, 'foo': 456, 'bar': 789}
        idx_map = util.make_values_to_index_map(data.values())
        self.assertEqual(len(idx_map), len(data))
        self.assertEqual(idx_map[123], 0)
        self.assertEqual(idx_map[456], 1)
        self.assertEqual(idx_map[789], 2)
