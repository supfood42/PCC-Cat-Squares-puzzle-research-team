# Cat Puzzle BFS C++ Port

This project ports the packed-piece Python functions to C++17.

## Packed formats

A piece is a `uint16_t` displayed as:

```text
[Top][Right][Bottom][Left]
 15-12 11-8   7-4    3-0
```

A target corner is a `uint8_t` displayed as:

```text
[required top][required left]
      7-4            3-0
```

A zero target nibble is a boundary wildcard: that side has no neighbor.

## Build

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

On Windows with Visual Studio, the executable is commonly under:

```text
build/Release/puzzle_solve_BFS.exe
```

## Run

```bash
puzzle_solve_BFS <puzzle_file> [seed] [max_cases]
```

Example:

```bash
puzzle_solve_BFS cats_10x10_1.txt 12345 1000000
```

`max_cases=0` means unlimited. BFS can consume very large amounts of memory, so a finite limit is advisable while testing.

The puzzle filename must contain `_NxN_numPuzzles`, and the text file must contain exactly `numPuzzles * n * n * 4` signed edge values.

## Important behavior

- The solver retains the Python code's single randomly selected starter piece. A failed run only proves that no branch survived from that starter. Use another seed to try another starter.
- Boundary zero nibbles are treated as wildcards. They mean “no neighbor on this side.”
- The diagonal changes from growing to shrinking when the current layer reaches `n - 1`; this avoids the extra boundary targets produced by `layer < n`.
- `Board(row, col)` is logically two-dimensional, but its storage is one contiguous vector for better cache locality.
