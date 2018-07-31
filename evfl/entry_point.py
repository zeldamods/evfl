from evfl.common import StringHolder
import evfl.event
from evfl.util import *

class EntryPoint(BinaryObject):
    __slots__ = ['name', 'main_event', '_sub_flow_event_indices', '_sub_flow_event_indices_offset_writer']
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.main_event: RequiredIndex[evfl.event.Event] = RequiredIndex()
        self._sub_flow_event_indices: typing.List[int] = []
        self._sub_flow_event_indices_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        sub_flow_event_indices_offset = stream.read_u64()
        x8 = stream.read_u64()
        ptr_x10 = stream.read_u64()
        num_sub_flow_event_indices = stream.read_u16()
        x1a = stream.read_u16()
        self.main_event._idx = stream.read_u16()
        x1e = stream.read_u16()
        assert x8 == 0 and x1a == 0 and x1e == 0 and ptr_x10 == 0

        if num_sub_flow_event_indices > 0:
            assert sub_flow_event_indices_offset != 0
            with SeekContext(stream, sub_flow_event_indices_offset):
                self._sub_flow_event_indices = [stream.read_u16() for i in range(num_sub_flow_event_indices)]

    def _do_write(self, stream: WriteStream) -> None:
        self._sub_flow_event_indices_offset_writer = stream.write_placeholder_ptr_if(bool(self._sub_flow_event_indices), register=True)
        stream.write(u64(0)) # x8
        stream.write_nullptr(register=True) # ptr_x10
        stream.write(u16(len(self._sub_flow_event_indices)))
        stream.write(u16(0)) # x1a
        stream.write(u16(self.main_event._idx))
        stream.write(u16(0)) # x1e

    def write_extra_data(self, stream: WriteStream) -> None:
        if self._sub_flow_event_indices_offset_writer:
            self._sub_flow_event_indices_offset_writer.write_current_offset(stream)
            for idx in self._sub_flow_event_indices:
                stream.write(u16(idx))
            stream.align(8)
        stream.skip(0x18)
