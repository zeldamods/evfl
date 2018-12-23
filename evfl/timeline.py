from evfl.actor import Actor
from evfl.container import Container
from evfl.common import StringHolder
from evfl.util import *

class Clip(BinaryObject):
    __slots__ = ['start_time', 'duration', 'actor', 'actor_action', 'xc', 'params', '_params_offset_writer']
    def __init__(self) -> None:
        super().__init__()
        self.start_time = -1.0
        self.duration = -1.0
        self.actor: RequiredIndex[Actor] = RequiredIndex()
        self.actor_action: RequiredIndex[StringHolder] = RequiredIndex()
        # TODO: figure out what this is
        self.xc = 0xff
        self.params: typing.Optional[Container] = None
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.start_time = stream.read_f32()
        self.duration = stream.read_f32()
        self.actor._idx = stream.read_u16()
        self.actor_action._idx = stream.read_u16()
        self.xc = stream.read_u8()
        stream.skip(3)
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(f32(self.start_time))
        stream.write(f32(self.duration))
        stream.write(u16(self.actor._idx))
        stream.write(u16(self.actor_action._idx))
        stream.write(u8(self.xc))
        stream.write(u8(0) * 3)
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))

    def write_extra_data(self, stream: WriteStream) -> None:
        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class Oneshot(BinaryObject):
    __slots__ = ['time', 'actor', 'actor_action', 'params', '_params_offset_writer']
    def __init__(self) -> None:
        super().__init__()
        self.time = -1.0
        self.actor: RequiredIndex[Actor] = RequiredIndex()
        self.actor_action: RequiredIndex[StringHolder] = RequiredIndex()
        self.params: typing.Optional[Container] = None
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.time = stream.read_f32()
        self.actor._idx = stream.read_u16()
        self.actor_action._idx = stream.read_u16()
        stream.skip(8)
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(f32(self.time))
        stream.write(u16(self.actor._idx))
        stream.write(u16(self.actor_action._idx))
        stream.write(u64(0))
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))

    def write_extra_data(self, stream: WriteStream) -> None:
        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class Cut(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.start_time = -1.0 # TODO: is this correct?
        self.x4 = 0xffffffff # TODO: what is this?
        self.name = ''
        self.params: typing.Optional[Container] = None
        self._params_offset_writer: typing.Optional[PlaceholderWriter] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.start_time = stream.read_f32()
        self.x4 = stream.read_u32()
        self.name = stream.read_string_ref()
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(f32(self.start_time))
        stream.write(u32(self.x4))
        stream.write_string_ref(self.name)
        self._params_offset_writer = stream.write_placeholder_ptr_if(bool(self.params))

    def write_extra_data(self, stream: WriteStream) -> None:
        if self._params_offset_writer and self.params:
            self._params_offset_writer.write_current_offset(stream)
            self.params.write(stream)

class Trigger(BinaryObject):
    __slots__ = ['clip', 'type']
    def __init__(self) -> None:
        super().__init__()
        self.clip: RequiredIndex[Clip] = RequiredIndex()
        self.type = 0xff

    def _do_read(self, stream: ReadStream) -> None:
        self.clip._idx = stream.read_u16()
        self.type = stream.read_u8()
        stream.skip(1)

    def _do_write(self, stream: WriteStream) -> None:
        stream.write(u16(self.clip._idx))
        stream.write(u8(self.type))
        stream.write(u8(0))

    def __repr__(self) -> str:
        return f'Trigger(clip={self.clip._idx}, type={self.type})'

class Subtimeline(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.name = ''

    def _do_read(self, stream: ReadStream) -> None:
        self.name = stream.read_string_ref()

    def _do_write(self, stream: WriteStream) -> None:
        stream.write_string_ref(self.name)

class Timeline(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.name = ''
        self.duration = -1.0
        self.actors: typing.List[Actor] = []
        self.clips: typing.List[Clip] = []
        self.oneshots: typing.List[Oneshot] = []
        self.triggers: typing.List[Trigger] = []
        self.subtimelines: typing.List[Subtimeline] = []
        self.cuts: typing.List[Cut] = []
        self.params: typing.Optional[Container] = None

        self._self_offset = -1

    def _do_read(self, stream: ReadStream) -> None:
        magic = stream.read_u32()
        string_pool_offset = stream.read_u32()
        x8 = stream.read_u32()
        xc = stream.read_u32()
        assert x8 == 0 and xc == 0
        self.duration = stream.read_f32()
        num_actors = stream.read_u16()
        num_actions = stream.read_u16()
        num_clips = stream.read_u16()
        num_oneshots = stream.read_u16()
        num_subtimelines = stream.read_u16()
        num_cuts = stream.read_u16()
        self.name = stream.read_string_ref()
        self.actors = stream.read_ptr_objects(Actor, num_actors)
        self.clips = stream.read_ptr_objects(Clip, num_clips)
        self.oneshots = stream.read_ptr_objects(Oneshot, num_oneshots)
        self.triggers = stream.read_ptr_objects(Trigger, 2 * num_clips)
        stream.align(8)
        self.subtimelines = stream.read_ptr_objects(Subtimeline, num_subtimelines)
        self.cuts = stream.read_ptr_objects(Cut, num_cuts)
        self.params = stream.read_ptr_object(Container)

        self._set_values_from_indexes()

    def _get_action_count(self) -> int:
        count = 0
        for actor in self.actors:
            count += len(actor.actions)
        return count

    def _set_values_from_indexes(self) -> None:
        for c in self.clips:
            c.actor.set_value(self.actors)
            c.actor_action.set_value(self.actors[c.actor._idx].actions)
        for o in self.oneshots:
            o.actor.set_value(self.actors)
            o.actor_action.set_value(self.actors[o.actor._idx].actions)
        for t in self.triggers:
            t.clip.set_value(self.clips)

    def _set_indexes_from_values(self) -> None:
        actor_to_idx = make_values_to_index_map(self.actors)
        clip_to_idx = make_values_to_index_map(self.clips)

        for c in self.clips:
            c.actor.set_index(actor_to_idx)
            c.actor_action._idx = c.actor.v.actions.index(c.actor_action.v)
        for o in self.oneshots:
            o.actor.set_index(actor_to_idx)
            o.actor_action._idx = o.actor.v.actions.index(o.actor_action.v)
        for t in self.triggers:
            t.clip.set_index(clip_to_idx)

    def _do_write(self, stream: WriteStream) -> None:
        self._set_indexes_from_values()

        for actor in self.actors:
            actor.write_extra_data(stream)
            stream.align(8)

        param_offset = None
        if self.params:
            param_offset = stream.tell()
            self.params.write(stream)

        # Header
        stream.align(8)
        self._self_offset = stream.tell()
        stream.write(b'TLIN')
        string_pool_rel_offset = stream.write_placeholder_u32()
        stream.write(u32(0)) # x8
        stream.write(u32(0)) # xc
        stream.write(f32(self.duration))
        stream.write(u16(len(self.actors)))
        stream.write(u16(self._get_action_count()))
        stream.write(u16(len(self.clips)))
        stream.write(u16(len(self.oneshots)))
        stream.write(u16(len(self.subtimelines)))
        stream.write(u16(len(self.cuts)))
        stream.write_string_ref(self.name)
        actors_offset_writer = stream.write_placeholder_ptr_if(bool(self.actors), register=True)
        clips_offset_writer = stream.write_placeholder_ptr_if(bool(self.clips), register=True)
        oneshots_offset_writer = stream.write_placeholder_ptr_if(bool(self.oneshots), register=True)
        triggers_offset_writer = stream.write_placeholder_ptr_if(bool(self.triggers), register=True)
        subtimelines_offset_writer = stream.write_placeholder_ptr_if(bool(self.subtimelines), register=True)
        cuts_offset_writer = stream.write_placeholder_ptr_if(bool(self.cuts), register=True)
        if param_offset:
            stream.register_pointer(stream.tell())
            stream.write(u64(param_offset))

        # Timeline structures
        writers: typing.List[typing.Tuple[typing.Optional[PlaceholderWriter], list]] = [
            (actors_offset_writer, self.actors),
            (clips_offset_writer, self.clips),
            (oneshots_offset_writer, self.oneshots),
            (subtimelines_offset_writer, self.subtimelines),
            (triggers_offset_writer, self.triggers),
            (cuts_offset_writer, self.cuts),
        ]
        for writer, array in writers:
            if writer:
                writer.write_current_offset(stream)
                for x in array:
                    x.write(stream)
                stream.align(8)

        # Extra data
        extra_data_arrays: typing.List[list] = [self.clips, self.oneshots, self.cuts]
        for xarray in extra_data_arrays:
            for x in xarray:
                x.write_extra_data(stream)
                stream.align(8)

        stream.align(8)
        string_pool_rel_offset.write(stream, u32(stream.tell() - self._self_offset))

    def _get_overriding_offset_to_self(self) -> int:
        return self._self_offset
