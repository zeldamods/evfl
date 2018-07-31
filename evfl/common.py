from evfl.util import *

class ActorIdentifier(BinaryObject):
    __slots__ = ['name', 'sub_name']
    def __init__(self, name: str = '', sub_name: str = '') -> None:
        super().__init__()
        self.name: str = name
        self.sub_name: str = sub_name

    def __str__(self) -> str:
        return f'{self.name}[{self.sub_name}]' if self.sub_name else self.name
    def __repr__(self) -> str:
        if not self.sub_name:
            return f'ActorIdentifier(name="{self.name}")'
        return f'ActorIdentifier(name="{self.name}", sub_name="{self.sub_name}")'

    def __hash__(self) -> int:
        return hash((self.name, self.sub_name))

    def __eq__(self, other) -> bool:
        return (self.name, self.sub_name) == (other.name, other.sub_name)

    def __ne__(self, other) -> bool:
        return not (self == other)

    def _do_read(self, stream: ReadStream) -> None:
        self.name = stream.read_string_ref()
        self.sub_name = stream.read_string_ref()

    def _do_write(self, stream: WriteStream) -> None:
        stream.write_string_ref(self.name)
        stream.write_string_ref(self.sub_name)

class Argument(str):
    pass

class StringHolder:
    __slots__ = ['v']
    def __init__(self, v='') -> None:
        self.v = v
    def __str__(self) -> str:
        return self.v
    def __hash__(self) -> int:
        return hash(self.v)
    def __eq__(self, other) -> bool:
        return self.v == other.v
    def __ne__(self, other) -> bool:
        return not (self == other)
