## File
* Header (0x48 bytes)
* `Flowchart*` array if it exists
* Flowchart DIC (always)
* `Timeline*` array if it exists
* Timeline DIC (always)

* Timeline
* Flowchart

* String pool (`STR `)
* Relocation table (`RELT`)

## Timeline
* TODO

## Flowchart
* Flowchart header
* Actors
    * Argument name is put in the string pool.
* Events
* Entry point DIC
* Entry points

* Event param containers, fork structs, etc. (in order)
* Actor param containers, string pointer arrays (in order)
* Entry point extra data
    * Sub flow event index arrays are written here
    * ptr_x10 data may be written here? (ptr_x10 has always been a nullptr in files I've checked.)
    * The size for each entry point is sizeof(event_idx_array) rounded up to the nearest
      multiple of 8 + 0x18 bytes.

## Container
* Container header (variable size)
* Container DIC
* Container items (+ values)
