from evfl.actor import Actor, ActorIdentifier
from evfl.dic import DicReader, DicWriter
from evfl.event import Event
from evfl.util import *

class EntryPoint(BinaryObject):
    __slots__ = ['main_event_idx', 'sub_flow_event_indices', '_sub_flow_event_indices_offset_writer']
    def __init__(self) -> None:
        super().__init__()
        self.main_event_idx = 0xffff
        self.sub_flow_event_indices: typing.List[int] = []
        self._sub_flow_event_indices_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        sub_flow_event_indices_offset = stream.read_u64()
        x8 = stream.read_u64()
        ptr_x10 = stream.read_u64()
        num_sub_flow_event_indices = stream.read_u16()
        x1a = stream.read_u16()
        self.main_event_idx = stream.read_u16()
        x1e = stream.read_u16()
        assert x8 == 0 and x1a == 0 and x1e == 0 and ptr_x10 == 0

        if num_sub_flow_event_indices > 0:
            assert sub_flow_event_indices_offset != 0
            with SeekContext(stream, sub_flow_event_indices_offset):
                self.sub_flow_event_indices = [stream.read_u16() for i in range(num_sub_flow_event_indices)]

    def _do_write(self, stream: WriteStream) -> None:
        self._sub_flow_event_indices_offset_writer = stream.write_placeholder_ptr_if(bool(self.sub_flow_event_indices), register=True)
        stream.write(u64(0)) # x8
        stream.write_nullptr(register=True) # ptr_x10
        stream.write(u16(len(self.sub_flow_event_indices)))
        stream.write(u16(0)) # x1a
        stream.write(u16(self.main_event_idx))
        stream.write(u16(0)) # x1e

    def write_extra_data(self, stream: WriteStream) -> None:
        if self._sub_flow_event_indices_offset_writer:
            self._sub_flow_event_indices_offset_writer.write_current_offset(stream)
            for idx in self.sub_flow_event_indices:
                stream.write(u16(idx))
            stream.align(8)
        stream.skip(0x18)

class Flowchart(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.name = ''
        self.actors: typing.Dict[ActorIdentifier, Actor] = dict()
        self.events: typing.Dict[str, Event] = dict()
        self.entry_points: typing.Dict[str, EntryPoint] = dict()

    def _do_read(self, stream: ReadStream) -> None:
        magic = stream.read_u32()
        string_pool_offset = stream.read_u32()
        x8 = stream.read_u32()
        xc = stream.read_u32()
        assert x8 == 0 and xc == 0
        num_actors = stream.read_u16()
        num_actions = stream.read_u16()
        num_queries = stream.read_u16()
        num_events = stream.read_u16()
        num_entry_points = stream.read_u16()
        x1a = stream.read_u16()
        x1c = stream.read_u16()
        x1e = stream.read_u16()
        assert x1a == 0 and x1c == 0 and x1e == 0
        self.name = stream.read_string_ref()

        with SeekContext(stream, stream.read_u64()):
            for i in range(num_actors):
                actor = Actor()
                actor.read(stream)
                self.actors[actor.identifier] = actor

        with SeekContext(stream, stream.read_u64()):
            for i in range(num_events):
                event = Event()
                event.read(stream)
                self.events[event.name] = event

        entry_point_dic = stream.read_ptr_object(DicReader)
        assert entry_point_dic is not None
        assert len(entry_point_dic.items) == num_entry_points

        with SeekContext(stream, stream.read_u64()):
            for entry_point_name in entry_point_dic.items:
                entry_point = EntryPoint()
                entry_point.read(stream)
                self.entry_points[entry_point_name] = entry_point

    def _get_action_count(self) -> int:
        count = 0
        for actor in self.actors.values():
            count += len(actor.actions)
        return count

    def _get_query_count(self) -> int:
        count = 0
        for actor in self.actors.values():
            count += len(actor.queries)
        return count

    def _do_write(self, stream: WriteStream) -> None:
        self_offset = stream.tell()
        stream.write(b'EVFL')
        string_pool_rel_offset = stream.write_placeholder_u32()
        stream.write(u32(0)) # x8
        stream.write(u32(0)) # xc
        stream.write(u16(len(self.actors)))
        stream.write(u16(self._get_action_count()))
        stream.write(u16(self._get_query_count()))
        stream.write(u16(len(self.events)))
        stream.write(u16(len(self.entry_points)))
        stream.write(u16(0)) # x1a
        stream.write(u16(0)) # x1c
        stream.write(u16(0)) # x1e
        stream.write_string_ref(self.name)
        actors_offset_writer = stream.write_placeholder_ptr_if(bool(self.actors), register=True)
        events_offset_writer = stream.write_placeholder_ptr_if(bool(self.events), register=True)
        entry_points_dic = DicWriter()
        entry_points_dic.write_placeholder_offset(stream)
        entry_points_offset_writer = stream.write_placeholder_ptr_if(bool(self.entry_points), register=True)

        # Actors
        if actors_offset_writer:
            actors_offset_writer.write_current_offset(stream)
            for actor in self.actors.values():
                actor.write(stream)

        # Events
        if events_offset_writer:
            events_offset_writer.write_current_offset(stream)
            for event in self.events.values():
                event.write(stream)

        # Entry point DIC
        for entry_point_name in self.entry_points.keys():
            entry_points_dic.insert(entry_point_name)
        entry_points_dic.write(stream)
        stream.align(8)

        # Entry points
        if entry_points_offset_writer:
            entry_points_offset_writer.write_current_offset(stream)
            for entry_point in self.entry_points.values():
                entry_point.write(stream)

        # Event data
        for event in self.events.values():
            stream.align(8)
            event.write_extra_data(stream)

        # Actor data
        for actor in self.actors.values():
            stream.align(8)
            actor.write_extra_data(stream)

        # Entry point data
        for entry_point in self.entry_points.values():
            stream.align(8)
            entry_point.write_extra_data(stream)

        stream.align(8)
        string_pool_rel_offset.write(stream, u32(stream.tell() - self_offset))
