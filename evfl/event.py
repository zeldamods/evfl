import abc
from evfl.container import Container
from evfl.enums import EventType
from evfl.util import *

class BaseEvent(metaclass=abc.ABCMeta):
    __slots__ = [] # type: ignore

    @abc.abstractmethod
    def _read(self, stream: ReadStream) -> None:
        pass

    @abc.abstractmethod
    def _write(self, stream: WriteStream) -> None:
        pass

    @abc.abstractmethod
    def _write_extra_data(self, stream: WriteStream) -> None:
        pass

class ActionEvent(BaseEvent):
    __slots__ = ['next_idx', 'actor_idx', 'actor_action_idx', 'params', '_params_offset_writer']
    def __init__(self) -> None:
        self.next_idx: int = 0xffff
        self.actor_idx: int = 0xffff
        self.actor_action_idx: int = 0xffff
        self.params: typing.Optional[Container] = None
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _read(self, stream: ReadStream) -> None:
        self.next_idx = stream.read_u16()
        self.actor_idx = stream.read_u16()
        self.actor_action_idx = stream.read_u16()
        self.params = stream.read_ptr_object(Container)
        unused_ptr_1 = stream.read_u64()
        unused_ptr_2 = stream.read_u64()
        assert unused_ptr_1 == 0 and unused_ptr_2 == 0

    def _write(self, stream: WriteStream) -> None:
        stream.write(u16(self.next_idx))
        stream.write(u16(self.actor_idx))
        stream.write(u16(self.actor_action_idx))
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))
        stream.write(u64(0))
        stream.write(u64(0))

    def _write_extra_data(self, stream: WriteStream) -> None:
        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class SwitchEvent(BaseEvent):
    __slots__ = ['actor_idx', 'actor_query_idx', 'params', 'cases', '_params_offset_writer', '_cases_offset_writer']
    def __init__(self) -> None:
        self.actor_idx = 0xffff
        self.actor_query_idx = 0xffff
        self.params: typing.Optional[Container] = None
        self.cases: typing.Dict[int, int] = dict()
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None
        self._cases_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _read(self, stream: ReadStream) -> None:
        num_cases = stream.read_u16() # can be zero.
        self.actor_idx = stream.read_u16()
        self.actor_query_idx = stream.read_u16()
        self.params = stream.read_ptr_object(Container)
        cases_offset = stream.read_u64()
        with SeekContext(stream, cases_offset):
            for i in range(num_cases):
                value = stream.read_u32()
                event_idx = stream.read_u16()
                self.cases[value] = event_idx
                stream.align(8)
        unused_ptr = stream.read_u64()
        assert unused_ptr == 0

    def _write(self, stream: WriteStream) -> None:
        stream.write(u16(len(self.cases))) # can be zero.
        stream.write(u16(self.actor_idx))
        stream.write(u16(self.actor_query_idx))
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))
        self._cases_offset_writer = stream.write_placeholder_ptr_if(bool(self.cases), register=True)
        stream.write(u64(0))

    def _write_extra_data(self, stream: WriteStream) -> None:
        # Nintendo's software writes the switch case struct first.
        if self._cases_offset_writer:
            stream.align(8)
            self._cases_offset_writer.write_current_offset(stream)
            for value, event_idx in self.cases.items():
                stream.write(u32(value))
                stream.write(u16(event_idx))
                stream.align(8)

        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class ForkEvent(BaseEvent):
    __slots__ = ['join_idx', 'forks', '_forks_offset_writer']
    def __init__(self) -> None:
        self.join_idx = 0xffff
        self.forks: typing.List[int] = []
        self._forks_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _read(self, stream: ReadStream) -> None:
        num_forks = stream.read_u16()
        self.join_idx = stream.read_u16()
        unused = stream.read_u16()
        assert unused == 0
        forks_offset = stream.read_u64()
        if num_forks == 0 or forks_offset == 0:
            raise ValueError('Fork event should have forks')
        with SeekContext(stream, forks_offset):
            self.forks = [stream.read_u16() for i in range(num_forks)]
        unused_ptr_1 = stream.read_u64()
        unused_ptr_2 = stream.read_u64()
        assert unused_ptr_1 == 0 and unused_ptr_2 == 0

    def _write(self, stream: WriteStream) -> None:
        assert self.forks
        stream.write(u16(len(self.forks)))
        stream.write(u16(self.join_idx))
        stream.write(u16(0)) # Unused
        self._forks_offset_writer = stream.write_placeholder_ptr()
        stream.write(u64(0))
        stream.write(u64(0))

    def _write_extra_data(self, stream: WriteStream) -> None:
        if self._forks_offset_writer:
            self._forks_offset_writer.write_current_offset(stream)
            for fork in self.forks:
                stream.write(u16(fork))
            stream.align(8)

class JoinEvent(BaseEvent):
    __slots__ = ['next_idx']
    def __init__(self) -> None:
        self.next_idx = 0xffff

    def _read(self, stream: ReadStream) -> None:
        self.next_idx = stream.read_u16()
        unused_xc = stream.read_u16()
        unused_xe = stream.read_u16()
        assert unused_xc == 0 and unused_xe == 0
        unused_params = stream.read_u64()
        unused_ptr_1 = stream.read_u64()
        unused_ptr_2 = stream.read_u64()
        assert unused_params == 0 and unused_ptr_1 == 0 and unused_ptr_2 == 0

    def _write(self, stream: WriteStream) -> None:
        stream.write(u16(self.next_idx))
        stream.write(u16(0))
        stream.write(u16(0))
        stream.write(u64(0))
        stream.write(u64(0))
        stream.write(u64(0))

    def _write_extra_data(self, stream: WriteStream) -> None:
        return

class SubFlowEvent(BaseEvent):
    __slots__ = ['next_idx', 'params', 'res_flowchart_name', 'entry_point_name', '_params_offset_writer']
    def __init__(self) -> None:
        self.next_idx = 0xffff
        self.params: typing.Optional[Container] = None
        self.res_flowchart_name = ''
        self.entry_point_name = ''
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _read(self, stream: ReadStream) -> None:
        self.next_idx = stream.read_u16()
        unused_xc = stream.read_u16()
        unused_xe = stream.read_u16()
        assert unused_xc == 0 and unused_xe == 0
        self.params = stream.read_ptr_object(Container)
        self.res_flowchart_name = stream.read_string_ref()
        self.entry_point_name = stream.read_string_ref()
        assert self.entry_point_name

    def _write(self, stream: WriteStream) -> None:
        stream.write(u16(self.next_idx))
        stream.write(u16(0)) # Unused
        stream.write(u16(0)) # Unused
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))
        assert self.entry_point_name
        stream.write_string_ref(self.res_flowchart_name)
        stream.write_string_ref(self.entry_point_name)

    def _write_extra_data(self, stream: WriteStream) -> None:
        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class Event(BinaryObject):
    __slots__ = ['name', 'data']
    def __init__(self) -> None:
        super().__init__()
        self.name = ''
        self.data: BaseEvent

    def _do_read(self, stream: ReadStream) -> None:
        self.name = stream.read_string_ref()
        etype = stream.read_u8()
        if etype == EventType.kAction:
            self.data = ActionEvent()
        elif etype == EventType.kSwitch:
            self.data = SwitchEvent()
        elif etype == EventType.kFork:
            self.data = ForkEvent()
        elif etype == EventType.kJoin:
            self.data = JoinEvent()
        elif etype == EventType.kSubFlow:
            self.data = SubFlowEvent()
        else:
            raise ValueError(f'Unknown event type: {etype}')
        stream.skip(1)
        self.data._read(stream)

    def _do_write(self, stream: WriteStream) -> None:
        stream.write_string_ref(self.name)
        if isinstance(self.data, ActionEvent):
            stream.write(u8(EventType.kAction))
        elif isinstance(self.data, SwitchEvent):
            stream.write(u8(EventType.kSwitch))
        elif isinstance(self.data, ForkEvent):
            stream.write(u8(EventType.kFork))
        elif isinstance(self.data, JoinEvent):
            stream.write(u8(EventType.kJoin))
        elif isinstance(self.data, SubFlowEvent):
            stream.write(u8(EventType.kSubFlow))
        stream.write(u8(0)) # Padding
        self.data._write(stream)

    def write_extra_data(self, stream: WriteStream) -> None:
        self.data._write_extra_data(stream)
