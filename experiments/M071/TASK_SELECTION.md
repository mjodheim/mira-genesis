# M071 fresh external-task selection

The rule frozen at commit `fa5d8962bce1659831f98938a194a226883d347c` was applied once to
the Git tree at `2fd12b88aafdd04a52c298e3940bcb189f9766d6`.

The tree contained 89 unique task identifiers. The two M070 identifiers were removed before
ranking, leaving 87 eligible identifiers. The canonical eligible-inventory digest is
`c21c3e62adfc08a80e33aa6506efa6e6bbd40e81a88c5a1bbb91603849d251c9`.

The selected order is:

1. `sqlite-with-gcov` — selection digest
   `013058dfbae753f97a6fb2aae47a8cb0cb662a6f935105e66dc74b8feb1cd8de`;
2. `custom-memory-heap-crash` — selection digest
   `04b44778a1b9acc9e9ccf912e76f0bf2ccc588302e0d43215bcce4f740ee9684`.

Selection enumerated only tracked `task.toml` paths and their parent identifiers. No selected task
configuration, instruction, environment, solution or verifier test had been opened or executed.
There is no replacement, retry or M071 scientific result at this boundary.
