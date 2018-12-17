from evfl.actor import Actor
from evfl.container import Container
from evfl.common import StringHolder
from evfl.util import *

class Clip(BinaryObject):
    __slots__ = ['start_time', 'duration', 'actor', 'actor_action', 'xc', 'params']
    def __init__(self) -> None:
        super().__init__()
        self.start_time = -1.0
        self.duration = -1.0
        self.actor: RequiredIndex[Actor] = RequiredIndex()
        self.actor_action: RequiredIndex[StringHolder] = RequiredIndex()
        # TODO: figure out what this is
        self.xc = 0xff
        self.params: typing.Optional[Container] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.start_time = stream.read_f32()
        self.duration = stream.read_f32()
        self.actor._idx = stream.read_u16()
        self.actor_action._idx = stream.read_u16()
        self.xc = stream.read_u8()
        stream.skip(3)
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        # FIXME: unimplemented
        raise NotImplementedError()

class Oneshot(BinaryObject):
    __slots__ = ['time', 'actor', 'actor_action', 'params']
    def __init__(self) -> None:
        super().__init__()
        self.time = -1.0
        self.actor: RequiredIndex[Actor] = RequiredIndex()
        self.actor_action: RequiredIndex[StringHolder] = RequiredIndex()
        self.params: typing.Optional[Container] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.time = stream.read_f32()
        self.actor._idx = stream.read_u16()
        self.actor_action._idx = stream.read_u16()
        stream.skip(8)
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        # FIXME: unimplemented
        raise NotImplementedError()

class Cut(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.duration = -1.0 # TODO: is this correct?
        self.x4 = 0xffffffff # TODO: what is this?
        self.name = ''
        self.params: typing.Optional[Container] = None

    def _do_read(self, stream: ReadStream) -> None:
        self.duration = stream.read_f32()
        self.x4 = stream.read_u32()
        self.name = stream.read_string_ref()
        self.params = stream.read_ptr_object(Container)

    def _do_write(self, stream: WriteStream) -> None:
        # FIXME: unimplemented
        raise NotImplementedError()

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
        # FIXME: unimplemented
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f'Trigger(clip={self.clip._idx}, type={self.type})'

class Subtimeline(BinaryObject):
    def __init__(self) -> None:
        super().__init__()
        self.name = ''

    def _do_read(self, stream: ReadStream) -> None:
        self.name = stream.read_string_ref()

    def _do_write(self, stream: WriteStream) -> None:
        # FIXME: unimplemented
        raise NotImplementedError()

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

    def _do_write(self, stream: WriteStream) -> None:
        # FIXME: unimplemented
        raise NotImplementedError()
