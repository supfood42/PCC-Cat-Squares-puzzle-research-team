# Edge-matching puzzle solver — C++ port

A C++17 port of the Python edge-matching-puzzle solver, focused on the
pipeline that actually solves puzzles:

| Python file(s)                    | C++ file      |
|------------------------------------|---------------|
| `code1_convert_pieces.py`, `puzzle_checks.py` | `puzzle.hpp` (parsing, corner IDs, global feasibility checks) |
| `piece_types.py`                   | `puzzle.hpp` (rotation grouping, canonical piece types) |
| `compatibility.py`                 | `puzzle.hpp` (candidate/edge compatibility, now as bitsets) |
| `scoring.py`                       | `stats.hpp` (boundary/position/corner-frequency scoring) |
| `frequency_stats.py` (scoring-relevant parts) | `stats.hpp` (learning tables) |
| `solver.py`                        | `solver.hpp`, `report.hpp`, `main.cpp` |

## What was intentionally left out, and why

- **`code2_generate_corner_sets.py`, `code3_check_2x2.py`, `corner_library.py`**
  were an earlier fixed-orientation-corner prototype for 2×2 puzzles only.
  `solver.py` itself loads this library but never uses it as a real
  constraint (`placement_is_valid` ignores it — see its own docstring).
  It isn't part of the live solving path, so it wasn't ported.
- **`piece_position_frequency`, `horizontal_pair_frequency`,
  `vertical_pair_frequency`, `block_frequency`** are recorded by
  `frequency_stats.py` but are never read back by `scoring.py` or
  `solver.py` — they only feed extra sections of the human-readable
  report. They were dropped to keep the learning file small; the tables
  that *do* affect search order (`corner_positions`, `junction_frequency`,
  `neighbor_candidate_frequency`) are fully ported.
- The interactive "delete the report file?" prompts were dropped —
  reports are just written each run.
- The persisted learning file uses a small custom text format
  (`frequency_stats.dat`) instead of JSON, so the build has zero external
  dependencies. It is **not** interchangeable with the Python project's
  `frequency_stats.json`.

If you want any of the above added back, it's a mechanical addition on
top of this structure — just ask.

## Why it's faster

The Python version repeatedly builds and intersects `set()` objects of
`(type_id, rotation_id)` tuples to compute each cell's legal-candidate
domain, at every node of the search tree. This port:

- Represents every candidate as an integer index and every domain as a
  fixed-size **bitset** (a few 64-bit words) — domain intersection
  becomes a handful of `AND` instructions instead of Python set
  operations (`bits.hpp`).
- Maintains the "which types still have inventory" mask incrementally
  (updated on place/undo) rather than rebuilt from scratch.
- Runs compiled, with no interpreter/object overhead per step.

On a randomly-generated 4×4 puzzle (16 solutions, exhaustive search):

| | Python | C++ (`-O3`) | Speedup |
|---|---|---|---|
| Time | 3.77 s | 0.051 s | **~74×** |
| Candidate attempts | 125,745 | 125,745 (identical) | — |

On a harder 5×5 case, both were given a 90-second budic budget:

| | Python | C++ |
|---|---|---|
| Recursive calls in 90 s | ~2,000,000 | ~267,000,000 |
| Calls/sec | ~22,000 | ~3,000,000 |

That's roughly **130× more search throughput**, which is what actually
matters for puzzles too large to fully explore in Python.

Candidate-attempt counts matched Python **exactly** on every test case
(2×2 → 8/8 solutions, 3×3 → 4/4 solutions with identical 1,290 candidate
attempts, 4×4 → 16/16 solutions with identical 125,745 attempts), which
is strong evidence the search logic is a faithful port, not just a
similar-looking rewrite.

## Build

```
g++ -O3 -std=c++17 -o puzzle_solver main.cpp
```
(All logic lives in the headers; `main.cpp` is the only translation unit.)

## Run

```
./puzzle_solver < pieces.txt
# or
./puzzle_solver pieces.txt
```

Input format is unchanged from the Python version: one piece per line,
`top right bottom left`, values from `{1,2,3,4,-1,-2,-3,-4}`, blank line
or EOF ends input. `gen_4x4.txt` is included as a ready-to-run example.

Output:
- Console summary (solution count, timing, search statistics).
- `solver_report_cpp.txt` — full report of the first stored solution,
  in the same spirit as `solver_report.txt`.
- `frequency_stats.dat` / `frequency_stats_report_cpp.txt` — the
  learning tables, updated after every run that finds a solution
  (mirrors the Python project learning across puzzles over time).

Tunables at the top of `main.cpp` (`MAX_SOLUTIONS`, `MAX_STORED_SOLUTIONS`,
`USE_CANDIDATE_SCORING`) mirror the equivalent settings in `solver.py`.
