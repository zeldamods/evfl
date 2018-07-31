import io
import os
import typing
import unittest

from evfl.evfl import EventFlow

def _open_test_file(name: str) -> typing.BinaryIO:
    return open(os.path.join(os.path.dirname(os.path.realpath(__file__)), name), 'rb')

class IntegrationTest(unittest.TestCase):
    def test(self) -> None:
        files = [
            # Simplest event flow file
            'GanonQuest.bfevfl',
            # Slightly more complex (entry points)
            'CompleteDungeon.bfevfl',
            # More complex
            'subchallnpc000_twin.bfevfl',
            # Special purpose event flow (Tips)
            'TipsCommon.bfevfl',
            # Special purpose event flow (AutoPlacementFlow)
            'AutoPlacement_Animal.bfevfl',
            # Has argument data types in its parameter containers
            'Common.bfevfl',
            # Test case for entry point extra data padding
            'Npc_HatenoVillage017.bfevfl',
            # UTF-8 Pascal strings
            'Npc_SouthHateru007.bfevfl',
            # Uses actor identifiers heavily
            'Animal_Forest.bfevfl',
            # Has a switch event with no cases (DummyQuery)
            'Demo346_0.bfevfl',
        ]

        for file in files:
            with self.subTest(file=file):
                with _open_test_file(f'original/{file}') as f:
                    data = f.read()

                flow = EventFlow()
                flow.read(data)
                stream = io.BytesIO()
                flow.write(stream)

                self.assertEqual(data, stream.getbuffer())
