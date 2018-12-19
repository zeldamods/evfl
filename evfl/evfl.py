import io
import struct
import typing

from evfl.dic import DicWriter
from evfl.flowchart import Flowchart
from evfl.timeline import Timeline
from evfl.util import *

class EventFlow:
    def __init__(self) -> None:
        self.name = ''
        self.flowchart: typing.Optional[Flowchart] = None
        self.timeline: typing.Optional[Timeline] = None

    def read(self, data: bytes) -> None:
        stream = ReadStream(data)

        magic = stream.read(8)
        if magic != b'BFEVFL\x00\x00':
            raise ValueError(f'Wrong magic: {magic.decode()} (expected BFEVFL\\x00\\x00)')

        version = stream.read_u16()
        if version != 0x0300:
            raise ValueError(f'Wrong version: 0x{version:x} (expected 0x0300)')

        xa = stream.read_u8()
        xb = stream.read_u8()
        if xa != 0:
            raise ValueError(f'Wrong xa: {xa} (expected 0)')

        bom = stream.read_u16()
        if bom != 0xfeff:
            raise ValueError('Wrong byte order mark (expected little endian)')

        alignment_shifted = stream.read_u8()
        xf = stream.read_u8()
        self.name = read_string(stream.data, stream.read_u32())
        is_relocated = stream.read_u16()
        first_block_offset = stream.read_u16()
        relocation_table_offset = stream.read_u32()
        file_size = stream.read_u32()

        num_flowcharts = stream.read_u16()
        num_timelines = stream.read_u16()
        assert 0 <= num_flowcharts <= 1 and 0 <= num_timelines <= 1

        x24 = stream.read_u32()
        assert x24 == 0

        flowchart_ptr_offset = stream.read_u64()
        flowchart_dic_offset = stream.read_u64()
        if num_flowcharts == 1:
            with SeekContext(stream, flowchart_ptr_offset):
                self.flowchart = stream.read_ptr_object(Flowchart)

        timeline_ptr_offset = stream.read_u64()
        timeline_dic_offset = stream.read_u64()
        if num_timelines == 1:
            with SeekContext(stream, timeline_ptr_offset):
                self.timeline = stream.read_ptr_object(Timeline)

    def write(self, underlying_stream: typing.BinaryIO) -> bool:
        stream = WriteStream(underlying_stream)

        if not ((self.flowchart or self.timeline) and not (self.flowchart and self.timeline)):
            return False

        # Header
        stream.write(b'BFEVFL\x00\x00')
        stream.write(u16(0x0300)) # Version
        stream.write(u8(0)) # Unknown
        stream.write(u8(0)) # Unknown
        stream.write(u16(0xfeff)) # BOM
        stream.write(u8(3)) # Alignment (shifted)
        stream.write(u8(0)) # Unknown
        stream.write_string_ref(self.name, is_header_name=True)
        stream.write(u16(0)) # 'Is relocated' flag (only set to one after relocation)
        first_block_offset_writer = stream.write_placeholder_u16()
        relocation_table_offset_writer = stream.write_placeholder_u32()
        file_size_writer = stream.write_placeholder_u32()
        stream.write(u16(1 if self.flowchart else 0))
        stream.write(u16(1 if self.timeline else 0))
        stream.write(u32(0)) # Unused?
        self._write_root_structure_metadata(stream)

        if self.flowchart:
            first_block_offset_writer.write(stream, u16(stream.tell()))
            self.flowchart.write(stream)

        if self.timeline:
            self.timeline.write(stream)
            first_block_offset_writer.write(stream, u16(self.timeline._self_offset))

        stream.finalise()
        file_size_writer.write(stream, u32(stream.tell()))
        relocation_table_offset_writer.write(stream, u32(stream.get_relocation_table_offset()))
        return True

    def _write_root_structure_metadata(self, stream: WriteStream) -> None:
        flowchart_array_offset_writer = stream.write_placeholder_ptr_if(bool(self.flowchart), register=True)
        flowchart_dic = DicWriter()
        if self.flowchart:
            flowchart_dic.insert(self.flowchart.name)
        flowchart_dic.write_placeholder_offset(stream)

        timeline_array_offset_writer = stream.write_placeholder_ptr_if(bool(self.timeline), register=True)
        timeline_dic = DicWriter()
        if self.timeline:
            timeline_dic.insert(self.timeline.name)
        timeline_dic.write_placeholder_offset(stream)

        if self.flowchart:
            flowchart_array_offset_writer.write_current_offset(stream)
            self.flowchart.write_placeholder_offset(stream)
        flowchart_dic.write(stream)
        if self.timeline:
            timeline_array_offset_writer.write_current_offset(stream)
            self.timeline.write_placeholder_offset(stream)
        timeline_dic.write(stream)
