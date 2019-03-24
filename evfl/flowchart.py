from collections import deque
from evfl.actor import Actor, ActorIdentifier
from evfl.container import Container
from evfl.dic import DicReader, DicWriter
from evfl.entry_point import EntryPoint
from evfl.event import Event, ActionEvent, SwitchEvent, ForkEvent, JoinEvent, SubFlowEvent
from evfl.util import *

class Flowchart(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.name = ''
        self.actors: typing.List[Actor] = []
        self.events: typing.List[Event] = []
        self.entry_points: typing.List[EntryPoint] = []

    def add_event(self, event: Event, idgen: IdGenerator):
        event.name = 'AutoEvent%d' % idgen.gen_id()
        self.events.append(event)

    """
    Add a chain of action events (automatically inserting WaitFrames when needed
    to give Breath of the Wild's event system a chance to clean up action contexts)
    and add an entry point to the first event in the chain.
    """
    def botw_add_action_chain_and_entry(self, entry_name: str, events: typing.List[Event],
                                        idgen: IdGenerator, actions_per_sequence=10) -> None:
        EventSystemActor = self.find_actor(ActorIdentifier('EventSystemActor'))
        WaitFrame = EventSystemActor.find_action('Demo_WaitFrame')

        def add_wait_frame_event(nxt: typing.Optional[Event]) -> Event:
            wait_evt = Event()
            wait_evt.data = ActionEvent()
            wait_evt.data.actor = make_rindex(EventSystemActor)
            wait_evt.data.actor_action = make_rindex(WaitFrame)
            wait_evt.data.params = Container()
            wait_evt.data.params.data['IsWaitFinish'] = True
            wait_evt.data.params.data['Frame'] = 1
            wait_evt.data.nxt = make_index(nxt)
            self.add_event(wait_evt, idgen)
            return wait_evt

        for evt in events:
            self.add_event(evt, idgen)

        for i in range(len(events) - 1):
            evt = events[i]
            assert isinstance(evt.data, ActionEvent)
            next_evt = events[i + 1]

            if i != 0 and (i + 1) % actions_per_sequence == 0:
                wait_evt = add_wait_frame_event(next_evt)
                evt.data.nxt = make_index(wait_evt)
            else:
                evt.data.nxt = make_index(next_evt)

        first_wait_evt = add_wait_frame_event(events[0])
        last_wait_evt = add_wait_frame_event(None)
        assert isinstance(events[-1].data, ActionEvent)
        events[-1].data.nxt = make_index(last_wait_evt)

        entry_point = EntryPoint(entry_name)
        entry_point.main_event = make_rindex(first_wait_evt)
        self.entry_points.append(entry_point)

    def find_actor(self, identifier: ActorIdentifier) -> Actor:
        for actor in self.actors:
            if actor.identifier == identifier:
                return actor
        raise ValueError(identifier)

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
        self.actors = stream.read_ptr_objects(Actor, num_actors)
        self.events = stream.read_ptr_objects(Event, num_events)

        entry_point_dic = stream.read_ptr_object(DicReader)
        assert entry_point_dic is not None
        assert len(entry_point_dic.items) == num_entry_points

        with SeekContext(stream, stream.read_u64()):
            for entry_point_name in entry_point_dic.items:
                entry_point = EntryPoint(entry_point_name)
                entry_point.read(stream)
                self.entry_points.append(entry_point)

        self._set_values_from_indexes()

    def _get_action_count(self) -> int:
        count = 0
        for actor in self.actors:
            count += len(actor.actions)
        return count

    def _get_query_count(self) -> int:
        count = 0
        for actor in self.actors:
            count += len(actor.queries)
        return count

    def _do_write(self, stream: WriteStream) -> None:
        self._set_indexes_from_values()

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
            for actor in self.actors:
                actor.write(stream)

        # Events
        if events_offset_writer:
            events_offset_writer.write_current_offset(stream)
            for event in self.events:
                event.write(stream)

        # Entry point DIC
        for entry_point in self.entry_points:
            entry_points_dic.insert(entry_point.name)
        entry_points_dic.write(stream)
        stream.align(8)

        # Entry points
        if entry_points_offset_writer:
            entry_points_offset_writer.write_current_offset(stream)
            for entry_point in self.entry_points:
                entry_point.write(stream)

        # Event data
        for event in self.events:
            stream.align(8)
            event.write_extra_data(stream)

        # Actor data
        for actor in self.actors:
            stream.align(8)
            actor.write_extra_data(stream)

        # Entry point data
        for entry_point in self.entry_points:
            stream.align(8)
            entry_point.write_extra_data(stream)

        stream.align(8)
        string_pool_rel_offset.write(stream, u32(stream.tell() - self_offset))

    def _set_values_from_indexes(self) -> None:
        # Yes, this is really ugly. I'm sorry.
        for actor in self.actors:
            actor.argument_entry_point.set_value(self.entry_points)

        for event in self.events:
            data = event.data
            if isinstance(data, ActionEvent):
                data.nxt.set_value(self.events)
                data.actor.set_value(self.actors)
                data.actor_action.set_value(self.actors[data.actor._idx].actions)
            elif isinstance(data, SwitchEvent):
                data.actor.set_value(self.actors)
                data.actor_query.set_value(self.actors[data.actor._idx].queries)
                for case in data.cases.values():
                    case.set_value(self.events)
            elif isinstance(data, ForkEvent):
                data.join.set_value(self.events)
                for fork in data.forks:
                    fork.set_value(self.events)
            elif isinstance(data, JoinEvent):
                data.nxt.set_value(self.events)
            elif isinstance(data, SubFlowEvent):
                data.nxt.set_value(self.events)

        for entry_point in self.entry_points:
            entry_point.main_event.set_value(self.events)

    def _set_indexes_from_values(self) -> None:
        actor_to_idx = make_values_to_index_map(self.actors)
        event_to_idx = make_values_to_index_map(self.events)
        entry_point_to_idx = make_values_to_index_map(self.entry_points)

        for actor in self.actors:
            actor.argument_entry_point.set_index(entry_point_to_idx)

        for event in self.events:
            data = event.data
            if isinstance(data, ActionEvent):
                data.nxt.set_index(event_to_idx)
                data.actor.set_index(actor_to_idx)
                data.actor_action._idx = data.actor.v.actions.index(data.actor_action.v)
            elif isinstance(data, SwitchEvent):
                data.actor.set_index(actor_to_idx)
                data.actor_query._idx = data.actor.v.queries.index(data.actor_query.v)
                for value, case in data.cases.items():
                    case.set_index(event_to_idx)
            elif isinstance(data, ForkEvent):
                data.join.set_index(event_to_idx)
                for fork in data.forks:
                    fork.set_index(event_to_idx)
            elif isinstance(data, JoinEvent):
                data.nxt.set_index(event_to_idx)
            elif isinstance(data, SubFlowEvent):
                data.nxt.set_index(event_to_idx)

        # A dict is used to have set-like properties *and* keep insertion order.
        def traverse_events(entry: Event, sub_flow_events: typing.Dict[Event, None], visited: typing.Set[Event]) -> None:
            """Traverse the event graph and collect sub flow events."""
            stack = deque([entry])
            while stack:
                event = stack.popleft()
                if event in visited:
                    continue
                visited.add(event)
                data = event.data
                if isinstance(data, ActionEvent):
                    if data.nxt.v:
                        stack.append(data.nxt.v)
                elif isinstance(data, SwitchEvent):
                    for value, case in data.cases.items():
                        traverse_events(case.v, sub_flow_events, visited)
                elif isinstance(data, ForkEvent):
                    for fork in data.forks:
                        traverse_events(fork.v, sub_flow_events, visited)
                    stack.append(data.join.v)
                elif isinstance(data, JoinEvent):
                    if data.nxt.v:
                        stack.append(data.nxt.v)
                elif isinstance(data, SubFlowEvent):
                    sub_flow_events[event] = None
                    if data.nxt.v:
                        stack.append(data.nxt.v)

        for entry_point in self.entry_points:
            entry_point.main_event.set_index(event_to_idx)
            sub_flow_events: typing.Dict[Event, None] = dict()
            traverse_events(entry_point.main_event.v, sub_flow_events, set())
            entry_point._sub_flow_event_indices = [event_to_idx[e] for e in sub_flow_events.keys()]
