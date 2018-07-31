# Library for parsing and writing Breath of the Wild Event Flow files

`evfl` is able to parse and rewrite every single flowchart event flow file (.bfevfl)
found in Breath of the Wild.

It is however currently not capable of reading timeline files (.bfevtm).

## Usage

```python
import evfl

flow = evfl.EventFlow()
with open('Animal_Master.bfevfl', 'rb') as file:
    flow.read(file.read())

flowchart = flow.flowchart
# Real documentation is nonexistent at the moment. I'm sorry.

with open('Animal_Master_Modified.bfevfl', 'wb') as modified_file:
    flow.write(modified_file)
```

## Tests

Unit and integration tests can be executed by running `python3 -m unittest discover`.

## License

This software is licensed under the terms of the GNU General Public License, version 2 or later.
