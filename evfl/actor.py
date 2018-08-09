from evfl.common import ActorIdentifier, StringHolder
from evfl.container import Container
from evfl.entry_point import EntryPoint
from evfl.util import *

class Actor(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.identifier = ActorIdentifier()
        # If specified, actor identifier arguments that are passed as parameters
        # with this argument name will bind to this actor.
        self.argument_name = ''
        # Entry point where this actor is used.
        self.argument_entry_point: Index[EntryPoint] = Index()
        self.actions: typing.List[StringHolder] = []
        self.queries: typing.List[StringHolder] = []
        self.params: typing.Optional[Container] = None
        # XXX: investigate what this is (set to 1 for flowcharts, but different for timeline actors)
        self.x36: int = 0xffff

        self._actions_offset_writer: typing.Optional[PlaceholderWriter] = None
        self._queries_offset_writer: typing.Optional[PlaceholderWriter] = None
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.identifier.read(stream)
        self.argument_name = stream.read_string_ref()
        actions_offset = stream.read_u64()
        queries_offset = stream.read_u64()
        self.params = stream.read_ptr_object(Container)
        num_actions = stream.read_u16()
        num_queries = stream.read_u16()
        self.argument_entry_point._idx = stream.read_u16()
        self.x36 = stream.read_u16()

        with SeekContext(stream, actions_offset):
            for i in range(num_actions):
                self.actions.append(StringHolder(stream.read_string_ref()))

        with SeekContext(stream, queries_offset):
            for i in range(num_queries):
                self.queries.append(StringHolder(stream.read_string_ref()))

    def _do_write(self, stream: WriteStream) -> None:
        self.identifier.write(stream)
        stream.write_string_ref(self.argument_name)
        self._actions_offset_writer = stream.write_placeholder_ptr_if(bool(self.actions), register=True)
        self._queries_offset_writer = stream.write_placeholder_ptr_if(bool(self.queries), register=True)
        # Yes, Nintendo inconsistency.
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))
        stream.write(u16(len(self.actions) if self.actions else 0))
        stream.write(u16(len(self.queries) if self.queries else 0))
        stream.write(u16(self.argument_entry_point._idx))
        stream.write(u16(self.x36))

    def write_extra_data(self, stream: WriteStream) -> None:
        """Writes the param container and string pointer arrays."""
        if self._params_offset_writer and self.params:
            stream.align(8)
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

        if self._actions_offset_writer and self.actions:
            stream.align(8)
            self._actions_offset_writer.write_current_offset(stream)
            for s in self.actions:
                stream.write_string_ref(s.v)

        if self._queries_offset_writer and self.queries:
            stream.align(8)
            self._queries_offset_writer.write_current_offset(stream)
            for s in self.queries:
                stream.write_string_ref(s.v)
