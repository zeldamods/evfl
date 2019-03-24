import abc
from collections import defaultdict
import io
import struct
import typing

_NUL_CHAR = b'\x00'

class IdGenerator:
    def __init__(self):
        self._id = 0
    def gen_id(self):
        r = self._id
        self._id += 1
        return r

T = typing.TypeVar('T')
class Index(typing.Generic[T]):
    __slots__ = ['v', '_idx']
    def __init__(self, idx: int = 0xffff) -> None:
        self.v: typing.Optional[T] = None
        self._idx = idx
    def set_value(self, values: typing.List[T]) -> None:
        self.v = values[self._idx] if self._idx != 0xffff else None
    def set_index(self, idx_map: typing.Dict[T, int]) -> None:
        self._idx = idx_map[self.v] if self.v else 0xffff

class RequiredIndex(typing.Generic[T]):
    __slots__ = ['v', '_idx']
    def __init__(self, idx: int = 0xffff) -> None:
        self.v: T
        self._idx = idx
    def set_value(self, values: typing.List[T]) -> None:
        self.v = values[self._idx]
    def set_index(self, idx_map: typing.Dict[T, int]) -> None:
        self._idx = idx_map[self.v]

def make_index(v: typing.Optional[T]) -> Index[T]:
    idx: Index[T] = Index()
    idx.v = v
    return idx

def make_rindex(v: T) -> RequiredIndex[T]:
    idx: RequiredIndex[T] = RequiredIndex()
    idx.v = v
    return idx

def make_values_to_index_map(iterable: typing.Iterable[T]) -> typing.Dict[T, int]:
    d: typing.Dict[T, int] = dict()
    for value in iterable:
        d[value] = len(d)
    return d

def align_up(n: int, align: int) -> int:
    return (n + align - 1) & -align

def u8(value: int) -> bytes:
    return struct.pack('B', value)
def u16(value: int) -> bytes:
    return struct.pack('<H', value)
def s16(value: int) -> bytes:
    return struct.pack('<h', value)
def u32(value: int) -> bytes:
    return struct.pack('<I', value)
def s32(value: int) -> bytes:
    return struct.pack('<i', value)
def u64(value: int) -> bytes:
    return struct.pack('<Q', value)
def s64(value: int) -> bytes:
    return struct.pack('<q', value)
def f32(value: float) -> bytes:
    return struct.pack('<f', value)
def pascal_string(data: str) -> bytes:
    raw_data = data.encode()
    return u16(len(raw_data)) + raw_data + _NUL_CHAR

def read_string(data: bytes, offset: int) -> str:
    end = data.find(_NUL_CHAR, offset) # type: ignore
    return data[offset:end].decode()

def read_pascal_string(data, offset: int) -> str:
    length: int = struct.unpack_from('<H', data, offset)[0]
    return bytes(data[offset+2:offset+2+length]).decode()

class Stream:
    __slots__ = ['_stream']
    def __init__(self, stream: typing.BinaryIO) -> None:
        self._stream = stream
    def seek(self, *args) -> None:
        self._stream.seek(*args)
    def tell(self) -> int:
        return self._stream.tell()
    def align(self, align: int) -> None:
        self.seek(align_up(self.tell(), align))
    def skip(self, n: int) -> None:
        self._stream.seek(n, 1)

class SeekContext:
    def __init__(self, stream: Stream, offset: int) -> None:
        self._stream = stream
        self._offset = offset
        self._original_offset = self._stream.tell()
    def __enter__(self):
        self._stream.seek(self._offset)
        return self._offset
    def __exit__(self, *args):
        self._stream.seek(self._original_offset)

class ReadStream(Stream):
    def __init__(self, data: bytes) -> None:
        stream = io.BytesIO(memoryview(data)) # type: ignore
        super().__init__(stream)
        self.data = data

    def read(self, *args) -> bytes:
        return self._stream.read(*args)

    def read_u8(self) -> int:
        return struct.unpack('B', self.read(1))[0]
    def read_u16(self) -> int:
        return struct.unpack('<H', self.read(2))[0]
    def read_u32(self) -> int:
        return struct.unpack('<I', self.read(4))[0]
    def read_s32(self) -> int:
        return struct.unpack('<i', self.read(4))[0]
    def read_u64(self) -> int:
        return struct.unpack('<Q', self.read(8))[0]
    def read_f32(self) -> float:
        return struct.unpack('<f', self.read(4))[0]
    def read_string_ref(self) -> str:
        ptr = self.read_u64()
        if ptr == 0:
            return ''
        return read_pascal_string(self.data, ptr)

    ReadObjectType = typing.TypeVar('ReadObjectType')
    def read_ptr_object(self, t: typing.Type[ReadObjectType], *args) -> typing.Optional[ReadObjectType]:
        ptr = self.read_u64()
        if ptr == 0:
            return None
        with SeekContext(self, ptr):
            obj = t(*args) # type: ignore
            obj.read(self) # type: ignore
        return obj

    def read_ptr_objects(self, t: typing.Type[ReadObjectType], n, *args) -> typing.List[ReadObjectType]:
        ptr = self.read_u64()
        if ptr == 0 or n == 0:
            return []
        result = []
        with SeekContext(self, ptr):
            for i in range(n):
                obj = t(*args) # type: ignore
                obj.read(self) # type: ignore
                result.append(obj)
        return result

class PlaceholderWriter:
    __slots__ = ['_offset']
    def __init__(self, offset: int) -> None:
        self._offset = offset
    def write(self, stream, data: bytes) -> None:
        current_pos = stream.tell()
        stream.seek(self._offset)
        stream.write(data)
        stream.seek(current_pos)
    def write_current_offset(self, stream) -> None:
        self.write(stream, u64(stream.tell()))

class WriteStream(Stream):
    class _StringRef(typing.NamedTuple):
        offset: int
        # The header string ref points to the C string (const char[]), not to PascalString.
        is_header_name: bool

    def __init__(self, stream: typing.BinaryIO) -> None:
        super().__init__(stream)
        self._pointers: typing.Set[int] = set()
        self._strings: typing.DefaultDict[str, typing.List[WriteStream._StringRef]] = defaultdict(list)
        # The empty string is always the first string.
        self._strings[''] = []
        self._relocation_table_offset = 0

    def register_string(self, s: str) -> None:
        self._strings[s]

    def register_pointer(self, offset) -> None:
        self._pointers.add(offset)

    def get_relocation_table_offset(self) -> int:
        return self._relocation_table_offset

    def write(self, data: bytes) -> None:
        self._stream.write(data)

    def write_nullptr(self, register=False) -> None:
        if register:
            self.register_pointer(self.tell())
        self.write(u64(0))

    def write_placeholder(self, placeholder_data: bytes) -> PlaceholderWriter:
        current_offset = self._stream.tell()
        self.write(placeholder_data)
        return PlaceholderWriter(current_offset)

    def write_placeholder_u16(self) -> PlaceholderWriter:
        return self.write_placeholder(u16(0xffff))
    def write_placeholder_u32(self) -> PlaceholderWriter:
        return self.write_placeholder(u32(0xffffffff))
    def write_placeholder_u64(self) -> PlaceholderWriter:
        return self.write_placeholder(u64(0xffffffffffffffff))

    def write_placeholder_ptr(self) -> PlaceholderWriter:
        self.register_pointer(self.tell())
        return self.write_placeholder_u64()

    def write_placeholder_ptr_if(self, condition: bool, register=False) -> PlaceholderWriter:
        if not condition:
            self.write_nullptr(register=register)
            return None # type: ignore
        return self.write_placeholder_ptr()

    def write_string_ref(self, data: str, is_header_name: bool = False) -> None:
        self._strings[data].append(self._StringRef(self.tell(), is_header_name))
        if is_header_name:
            self.write(u32(0xffffffff))
        else:
            self.register_pointer(self.tell())
            self.write(u64(0xffffffffffffffff))

    def finalise(self) -> None:
        self.align(8)
        self._write_string_pool()

        data_end = self.tell()
        self.align(8)
        self._write_relocation_table(data_end)

    def _write_string_pool(self) -> None:
        self.write(b'STR ')
        self.write(u32(0)) # Unused
        self.write(u64(0)) # Unused
        # The empty string is not counted.
        self.write(u32(len(self._strings) - 1))

        def sort_string(s: str):
            # XXX: Slow.
            return bin(int.from_bytes(s.encode(), byteorder='big'))[2:][::-1]

        for string in sorted(self._strings.keys(), key=sort_string):
            offset = self.tell()
            for ref in self._strings[string]:
                self.seek(ref.offset)
                self.write(u32(offset + 2) if ref.is_header_name else u64(offset))
            self.seek(offset)
            self.write(pascal_string(string))
            self.align(2)

    def _write_relocation_table(self, data_end: int) -> None:
        # Table
        self._relocation_table_offset = self.tell()
        self.write(b'RELT')
        self.write(u32(self._relocation_table_offset))
        # It's extremely unlikely that the number of entries will ever exceed 2^32 - 1,
        # so assume that only one section is needed.
        # (If a file does have that many sections, you should probably worry about the
        # offsets being 32 bit instead.)
        self.write(u32(1))
        self.write(u32(0)) # Padding

        # First section
        self.write(u64(0)) # Alternate offset (unused by Nintendo)
        self.write(u32(0)) # Used to calculate the base pointer for the alternate method (unused)
        self.write(u32(data_end))
        self.write(u32(0)) # Entries to skip
        num_entries_writer: PlaceholderWriter = self.write_placeholder_u32()

        # Section entries
        num_entries = 0
        pointers = set(self._pointers)
        pointers_list: typing.List[int] = sorted(pointers)
        for p in pointers_list:
            if p not in pointers: # Already processed.
                continue
            # As a space optimisation, each entry can cover up to 32 contiguous pointers.
            # A bitflag is used to indicate which pointers are valid and need relocation.
            # Try to process as many pointers as possible with a single entry.
            flag = 0
            for i in range(0x20):
                address = p + 8*i
                if address in pointers:
                    flag |= 1 << i
                    pointers.remove(address)
            self.write(u32(p))
            self.write(u32(flag))
            num_entries += 1

        num_entries_writer.write(self, u32(num_entries))

class BinaryObject(metaclass=abc.ABCMeta):
    __slots__ = ['_offsets_to_this']
    def __init__(self) -> None:
        self._offsets_to_this: typing.List[int] = []

    def write_placeholder_offset(self, stream: WriteStream) -> None:
        self._offsets_to_this.append(stream.tell())
        stream.register_pointer(stream.tell())
        stream.write(u64(0xffffffffffffffff))

    @abc.abstractmethod
    def _do_read(self, stream: ReadStream) -> None:
        pass

    @abc.abstractmethod
    def _do_write(self, stream: WriteStream) -> None:
        pass

    def _get_overriding_offset_to_self(self) -> int:
        return -1

    def read(self, stream: ReadStream) -> None:
        self._do_read(stream)

    def write(self, stream: WriteStream) -> None:
        start_pos = stream.tell()
        self._do_write(stream)
        end_pos = stream.tell()

        stream.seek(start_pos)
        value = self._get_overriding_offset_to_self()
        if value == -1:
            value = start_pos
        for offset in self._offsets_to_this:
            stream.seek(offset)
            stream.write(u64(value))
        stream.seek(end_pos)
