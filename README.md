# Library for parsing and writing Nintendo EventFlow binary files

`evfl` is able to parse and rewrite every single event flow found in
*Breath of the Wild*, both flowcharts (bfevfl) and timelines (bfevtm).

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
