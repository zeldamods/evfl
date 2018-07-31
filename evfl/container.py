import typing

from evfl.common import ActorIdentifier, Argument
from evfl.dic import DicReader, DicWriter
from evfl.enums import ContainerDataType
from evfl.util import *

ContainerDataPyTypes = typing.Union[
    int, bool, float, str, Argument, ActorIdentifier,
    typing.List[int], typing.List[bool], typing.List[float], typing.List[str],
]

class Container(BinaryObject):
    __slots__ = ['data']
    def __init__(self) -> None:
        super().__init__()
        self.data: typing.Dict[str, ContainerDataPyTypes] = dict()

    def _do_read(self, stream: ReadStream) -> None:
        data_type = stream.read_u8()
        if data_type != ContainerDataType.kContainer:
            raise ValueError('Invalid data type (expected kContainer)')
        stream.skip(1)
        num_items = stream.read_u16()
        x4 = stream.read_u32()
        assert x4 == 0
        dic = stream.read_ptr_object(DicReader)
        assert dic
        for name in dic.items:
            with SeekContext(stream, stream.read_u64()) as item_offset:
                self.data[name] = self._read_item(stream)

    def _read_item(self, stream: ReadStream) -> ContainerDataPyTypes:
        data_type = stream.read_u8()
        stream.skip(1)
        num_items = stream.read_u16()
        x4 = stream.read_u32()
        assert x4 == 0
        dic_offset = stream.read_u64()
        assert dic_offset == 0

        if data_type == ContainerDataType.kInt:
            return stream.read_s32()
        if data_type == ContainerDataType.kIntArray:
            return [stream.read_s32() for i in range(num_items)]

        if data_type == ContainerDataType.kBool:
            return bool(stream.read_s32())
        if data_type == ContainerDataType.kBoolArray:
            return [bool(stream.read_s32()) for i in range(num_items)]

        if data_type == ContainerDataType.kFloat:
            return stream.read_f32()
        if data_type == ContainerDataType.kFloatArray:
            return [stream.read_f32() for i in range(num_items)]

        if data_type == ContainerDataType.kString:
            return stream.read_string_ref()
        if data_type == ContainerDataType.kStringArray:
            return [stream.read_string_ref() for i in range(num_items)]

        if data_type == ContainerDataType.kArgument:
            return Argument(stream.read_string_ref())

        if data_type == ContainerDataType.kActorIdentifier:
            actor_identifier = ActorIdentifier()
            actor_identifier.read(stream)
            return actor_identifier

        if data_type == ContainerDataType.kContainer:
            raise ValueError('Unexpected container')

        if data_type == ContainerDataType.kWString or data_type == ContainerDataType.kWStringArray:
            raise ValueError(f'Unhandled data type: wide string or wide string array ({data_type})')

        raise ValueError(f'Unknown data type: {data_type}')

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(u8(ContainerDataType.kContainer))
        stream.write(u8(0)) # Padding
        stream.write(u16(len(self.data)))
        stream.write(u32(0)) # Unused

        dic = DicWriter()
        for key in self.data.keys():
            dic.insert(key)
        dic.write_placeholder_offset(stream)

        item_ptr_writers: typing.List[PlaceholderWriter] = []
        for i in range(len(self.data)):
            item_ptr_writers.append(stream.write_placeholder_ptr())

        dic.write(stream)

        for ptr_writer, value in zip(item_ptr_writers, self.data.values()):
            stream.align(8)
            ptr_writer.write_current_offset(stream)
            self._write_item(stream, value)

    def _write_item_common_header(self, stream: WriteStream, data_type, num_items: int) -> None:
        stream.write(u8(data_type))
        stream.write(u8(0)) # Padding
        stream.write(u16(num_items))
        stream.write(u32(0)) # Unused
        stream.write(u64(0)) # DIC pointer

    def _write_item(self, stream: WriteStream, value: ContainerDataPyTypes) -> None:
        # Must come first because bool is derived from int.
        if isinstance(value, bool):
            self._write_item_common_header(stream, ContainerDataType.kBool, 1)
            stream.write(u32(0x80000001 if value else 0))

        elif isinstance(value, int):
            self._write_item_common_header(stream, ContainerDataType.kInt, 1)
            stream.write(s32(value))

        elif isinstance(value, float):
            self._write_item_common_header(stream, ContainerDataType.kFloat, 1)
            stream.write(f32(value))

        # Yes, for some reason strings that appear in containers are not put into the string pool.
        # Nintendo is really consistent at being inconsistent.
        elif isinstance(value, str):
            if isinstance(value, Argument):
                self._write_item_common_header(stream, ContainerDataType.kArgument, 1)
            else:
                self._write_item_common_header(stream, ContainerDataType.kString, 1)
            ptr_writer = stream.write_placeholder_ptr()
            ptr_writer.write_current_offset(stream)
            stream.write(pascal_string(value))

        elif isinstance(value, ActorIdentifier):
            # An actor identifier is treated as two strings.
            self._write_item_common_header(stream, ContainerDataType.kActorIdentifier, 2)
            ptr_writer1 = stream.write_placeholder_ptr()
            ptr_writer2 = stream.write_placeholder_ptr()
            ptr_writer1.write_current_offset(stream)
            stream.write(pascal_string(value.name))
            # But unlike regular string arrays, the strings are aligned to 2-byte boundaries.
            # Yes, Nintendo inconsistency strikes again.
            stream.align(2)
            ptr_writer2.write_current_offset(stream)
            stream.write(pascal_string(value.sub_name))

        elif isinstance(value, list):
            if isinstance(value[0], int):
                self._write_item_common_header(stream, ContainerDataType.kIntArray, len(value))
                for v in value:
                    stream.write(s32(v))

            elif isinstance(value[0], bool):
                self._write_item_common_header(stream, ContainerDataType.kBoolArray, len(value))
                for v in value:
                    stream.write(s32(1 if v else 0))

            elif isinstance(value[0], float):
                self._write_item_common_header(stream, ContainerDataType.kFloatArray, len(value))
                for v in value:
                    stream.write(f32(v)) # type: ignore

            elif isinstance(value[0], str):
                self._write_item_common_header(stream, ContainerDataType.kStringArray, len(value))
                ptr_writers: typing.List[PlaceholderWriter] = []
                for i in range(len(value)):
                    ptr_writers.append(stream.write_placeholder_ptr())
                for ptr_writer, v in zip(ptr_writers, value):
                    stream.align(8)
                    ptr_writer.write_current_offset(stream)
                    stream.write(pascal_string(v)) # type: ignore

            else:
                raise ValueError(f'Invalid array data type')

        else:
            raise ValueError(f'Invalid data type')
