import time
from collections import Counter
from pathlib import Path

from puzzle_checks import (
    determine_board_size,
    parse_piece_text,
    run_global_checks,
)

from piece_types import (
    build_piece_types,
    create_piece_inventory,
)

from compatibility import (
    prepare_compatibility,
    filter_by_remaining_inventory,
)

from corner_library import load_corner_library

from scoring import (
    calculate_symbol_discrepancy,
    combined_candidate_score,
    describe_discrepancy,
)

from frequency_stats import (
    load_statistics,
    record_solution_statistics,
    write_frequency_report,
)


# ============================================================
# SETTINGS
# ============================================================

PROJECT_FOLDER = Path(__file__).resolve().parent

SOLUTION_REPORT_FILE = (
    PROJECT_FOLDER
    / "solver_report.txt"
)

# For large puzzles, use 1.
# For testing every 2 x 2 orientation-specific solution,
# use a larger number such as 100.
MAX_SOLUTIONS = 1

# ============================================================
# PERFORMANCE SETTINGS
# ============================================================

# True when you want the first solution quickly.
# False when you want to count many/all solutions.
USE_CANDIDATE_SCORING = True

# Print one progress line after this many solutions.
# Use None to disable.
SOLUTION_PROGRESS_INTERVAL = 40

# Print a heartbeat after this many recursive calls.
# Use None to disable.
SEARCH_HEARTBEAT_INTERVAL = 1_000_000

# Save only this many complete boards in memory.
# The solver can still count more solutions.
MAX_STORED_SOLUTIONS = 1

# Write detailed information for only this many solutions.
MAX_DETAILED_REPORT_SOLUTIONS = 1

# ============================================================
# INPUT
# ============================================================

def get_piece_input() -> list[list[int]]:
    """
    Read all puzzle pieces from the terminal.

    Each line must use this order:
        top right bottom left

    Input ends when the user enters a blank line.
    """

    print("Paste all puzzle pieces.")
    print("Use one piece per line:")
    print("top right bottom left")
    print()
    print("Press Enter on a blank line when finished.")
    print()

    lines = []

    while True:
        line = input()

        if not line.strip():
            break

        lines.append(line)

    return parse_piece_text(
        "\n".join(lines)
    )


# ============================================================
# GRID HELPERS
# ============================================================

def grid_index(
    row: int,
    column: int,
    n: int,
) -> int:
    """
    Convert row and column into a one-dimensional index.
    """

    return row * n + column


def candidate_at(
    grid: list,
    row: int,
    column: int,
    n: int,
):
    """
    Return the candidate key stored at one grid position.

    Candidate key:
        (piece_type_id, rotation_id)
    """

    return grid[
        grid_index(
            row,
            column,
            n,
        )
    ]


def get_candidate_edges(
    candidate_key: tuple[int, int],
    candidates: dict,
) -> tuple[int, int, int, int]:
    """
    Return edges in this order:

        top
        right
        bottom
        left
    """

    return candidates[
        candidate_key
    ]["edges"]


def get_candidate_corners(
    candidate_key: tuple[int, int],
    candidates: dict,
) -> tuple[int, int, int, int]:
    """
    Return corners in this order:

        top-left
        top-right
        bottom-right
        bottom-left
    """

    return candidates[
        candidate_key
    ]["corners"]


# ============================================================
# EXACT EDGE MATCHING
# ============================================================

def edges_match(
    first_edge: int,
    second_edge: int,
) -> bool:
    """
    Two edges match when they have the same color and
    opposite signs.
    """

    return first_edge == -second_edge


def placement_is_valid(
    grid: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
    corner_library: dict,
) -> bool:
    """
    Check the newly placed candidate against every already
    filled neighboring position.

    Direct edge matching is the authoritative rule.

    The corner library is intentionally not used as a hard
    validity condition because the previous corner-orientation
    convention was inconsistent with physical edge placement.
    """

    current_key = candidate_at(
        grid,
        row,
        column,
        n,
    )

    if current_key is None:
        return False

    top, right, bottom, left = (
        get_candidate_edges(
            current_key,
            candidates,
        )
    )

    # Check the piece above.
    if row > 0:
        above_key = candidate_at(
            grid,
            row - 1,
            column,
            n,
        )

        if above_key is not None:
            above_bottom = get_candidate_edges(
                above_key,
                candidates,
            )[2]

            if not edges_match(
                above_bottom,
                top,
            ):
                return False

    # Check the piece to the right.
    if column < n - 1:
        right_key = candidate_at(
            grid,
            row,
            column + 1,
            n,
        )

        if right_key is not None:
            right_left = get_candidate_edges(
                right_key,
                candidates,
            )[3]

            if not edges_match(
                right,
                right_left,
            ):
                return False

    # Check the piece below.
    if row < n - 1:
        below_key = candidate_at(
            grid,
            row + 1,
            column,
            n,
        )

        if below_key is not None:
            below_top = get_candidate_edges(
                below_key,
                candidates,
            )[0]

            if not edges_match(
                bottom,
                below_top,
            ):
                return False

    # Check the piece to the left.
    if column > 0:
        left_key = candidate_at(
            grid,
            row,
            column - 1,
            n,
        )

        if left_key is not None:
            left_right = get_candidate_edges(
                left_key,
                candidates,
            )[1]

            if not edges_match(
                left_right,
                left,
            ):
                return False

    return True


# ============================================================
# CANDIDATE SELECTION
# ============================================================

def candidates_for_position(
    grid: list,
    row: int,
    column: int,
    n: int,
    all_candidate_keys: set[tuple[int, int]],
    compatibility: dict,
    remaining_inventory: Counter,
) -> list[tuple[int, int]]:
    """
    Return candidates compatible with every already filled
    neighbor around one empty position.
    """

    possible = set(
        all_candidate_keys
    )

    # Neighbor above.
    if row > 0:
        above_key = candidate_at(
            grid,
            row - 1,
            column,
            n,
        )

        if above_key is not None:
            possible &= compatibility[
                above_key
            ]["below"]

    # Neighbor to the right.
    if column < n - 1:
        right_key = candidate_at(
            grid,
            row,
            column + 1,
            n,
        )

        if right_key is not None:
            possible &= compatibility[
                right_key
            ]["left"]

    # Neighbor below.
    if row < n - 1:
        below_key = candidate_at(
            grid,
            row + 1,
            column,
            n,
        )

        if below_key is not None:
            possible &= compatibility[
                below_key
            ]["above"]

    # Neighbor to the left.
    if column > 0:
        left_key = candidate_at(
            grid,
            row,
            column - 1,
            n,
        )

        if left_key is not None:
            possible &= compatibility[
                left_key
            ]["right"]

    possible = filter_by_remaining_inventory(
        possible,
        remaining_inventory,
    )

    return sorted(
        possible
    )


def choose_next_position(
    grid: list,
    n: int,
    all_candidate_keys: set[tuple[int, int]],
    compatibility: dict,
    remaining_inventory: Counter,
) -> tuple[
    int,
    int,
    list[tuple[int, int]],
] | None:
    """
    Choose the empty position with the fewest legal candidates.

    This is the most-constrained-position strategy.

    Returns:
        row
        column
        candidate list

    Returns None when the board is full.
    """

    best_position = None
    best_candidates = None

    for row in range(n):
        for column in range(n):
            position = grid_index(
                row,
                column,
                n,
            )

            if grid[position] is not None:
                continue

            candidates_here = candidates_for_position(
                grid=grid,
                row=row,
                column=column,
                n=n,
                all_candidate_keys=all_candidate_keys,
                compatibility=compatibility,
                remaining_inventory=remaining_inventory,
            )

            # A position with zero candidates proves that
            # the current branch is impossible.
            if not candidates_here:
                return (
                    row,
                    column,
                    [],
                )

            if (
                best_candidates is None
                or len(candidates_here)
                < len(best_candidates)
            ):
                best_position = (
                    row,
                    column,
                )

                best_candidates = (
                    candidates_here
                )

                # One candidate is the strongest possible MRV result.
                if len(best_candidates) == 1:
                    return (
                        row,
                        column,
                        best_candidates,
                    )

    if best_position is None:
        return None

    return (
        best_position[0],
        best_position[1],
        best_candidates,
    )


# ============================================================
# CORNER AND JUNCTION HELPERS
# ============================================================

def completed_junction(
    grid: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
):
    """
    Return the four corner IDs around an internal crossing.

    Arrangement:

        A B
        C D

    Returned clockwise order:

        A bottom-right
        B bottom-left
        D top-left
        C top-right

    The given row and column identify D, the bottom-right
    piece of the 2 x 2 block.
    """

    if row == 0 or column == 0:
        return None

    a_key = candidate_at(
        grid,
        row - 1,
        column - 1,
        n,
    )

    b_key = candidate_at(
        grid,
        row - 1,
        column,
        n,
    )

    c_key = candidate_at(
        grid,
        row,
        column - 1,
        n,
    )

    d_key = candidate_at(
        grid,
        row,
        column,
        n,
    )

    if any(
        key is None
        for key in (
            a_key,
            b_key,
            c_key,
            d_key,
        )
    ):
        return None

    a_corners = get_candidate_corners(
        a_key,
        candidates,
    )

    b_corners = get_candidate_corners(
        b_key,
        candidates,
    )

    c_corners = get_candidate_corners(
        c_key,
        candidates,
    )

    d_corners = get_candidate_corners(
        d_key,
        candidates,
    )

    return (
        a_corners[2],
        b_corners[3],
        d_corners[0],
        c_corners[1],
    )


def completed_junctions_touching_position(
    grid: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
) -> list[tuple[int, int, int, int]]:
    """
    Return every complete internal junction touching the
    newly placed position.

    One placement can complete up to four junctions.
    """

    junctions = []

    possible_bottom_right_positions = [
        (row, column),
        (row, column + 1),
        (row + 1, column),
        (row + 1, column + 1),
    ]

    for bottom_row, bottom_column in (
        possible_bottom_right_positions
    ):
        if not (
            1 <= bottom_row < n
            and 1 <= bottom_column < n
        ):
            continue

        junction = completed_junction(
            grid=grid,
            row=bottom_row,
            column=bottom_column,
            n=n,
            candidates=candidates,
        )

        if junction is not None:
            junctions.append(
                junction
            )

    return junctions


def learned_junction_score(
    grid: list,
    row: int,
    column: int,
    n: int,
    candidates: dict,
    frequency_statistics: dict,
) -> float:
    """
    Score newly completed junctions using previously recorded
    solution frequencies.

    This affects candidate order only.
    """

    if (
        frequency_statistics.get(
            "solutions_recorded",
            0,
        )
        == 0
    ):
        return 0.0

    score = 0.0

    junctions = completed_junctions_touching_position(
        grid=grid,
        row=row,
        column=column,
        n=n,
        candidates=candidates,
    )

    for junction in junctions:
        key = ",".join(
            str(value)
            for value in junction
        )

        count = frequency_statistics[
            "junction_frequency"
        ].get(
            key,
            0,
        )

        score += count

    return score


def learned_neighbor_score(
    grid: list,
    row: int,
    column: int,
    n: int,
    candidate_key: tuple[int, int],
    candidates: dict,
    frequency_statistics: dict,
) -> float:
    """
    Score a candidate using recorded top/left-neighbor patterns.

    This only changes search order. It never rejects a candidate.
    """

    frequency_table = frequency_statistics.get(
        "neighbor_candidate_frequency",
        {},
    )

    if not frequency_table:
        return 0.0

    candidate_value = ",".join(
        str(edge)
        for edge in candidates[candidate_key]["edges"]
    )

    if row > 0:
        top_key = candidate_at(grid, row - 1, column, n)
        if top_key is None:
            top_value = "EMPTY"
        else:
            top_value = ",".join(
                str(edge)
                for edge in candidates[top_key]["edges"]
            )
    else:
        top_value = "BOUNDARY"

    if column > 0:
        left_key = candidate_at(grid, row, column - 1, n)
        if left_key is None:
            left_value = "EMPTY"
        else:
            left_value = ",".join(
                str(edge)
                for edge in candidates[left_key]["edges"]
            )
    else:
        left_value = "BOUNDARY"

    key = (
        f"top={top_value}|"
        f"left={left_value}|"
        f"candidate={candidate_value}"
    )

    return float(frequency_table.get(key, 0))


# ============================================================
# SOLVER
# ============================================================

def solve_puzzle(
    n: int,
    piece_types: list[dict],
    candidates: dict,
    compatibility: dict,
    corner_library: dict,
    initial_inventory: Counter,
    discrepancy: dict[int, int],
    frequency_statistics: dict,
    max_solutions: int = 1,
) -> tuple[list[list], dict]:
    """
    Solve an n x n puzzle using:

        duplicate-piece inventory
        distinct rotations
        compatibility indexes
        most-constrained-position search
        boundary priority scoring
        learned corner and junction scoring
        recursive backtracking

    The solver stops when max_solutions solutions have been
    found or when the complete search space is exhausted.
    """

    # piece_types remains a parameter because tests and future
    # optimizations may use it, even though this version does not
    # directly inspect the list.
    _ = piece_types
    _ = corner_library

    grid = [
        None
        for _ in range(n * n)
    ]

    remaining_inventory = Counter(
        initial_inventory
    )

    all_candidate_keys = set(
        candidates.keys()
    )

    candidate_rarity = {}
    for candidate_key in all_candidate_keys:
        compatibility_data = compatibility[candidate_key]
        total_options = (
            len(compatibility_data["above"])
            + len(compatibility_data["right"])
            + len(compatibility_data["below"])
            + len(compatibility_data["left"])
        )
        candidate_rarity[candidate_key] = 1.0 / max(total_options, 1)

    solutions = []

    use_frequency_scoring = (
        frequency_statistics.get(
            "solutions_recorded",
            0,
        )
        > 0
    )
    solution_count = 0

    statistics = {
        "recursive_calls": 0,
        "candidate_attempts": 0,
        "placements_accepted": 0,
        "backtracks": 0,
        "dead_ends": 0,
        "stopped_at_solution_limit": False,
    }

    def candidate_search_score(
        candidate_key: tuple[int, int],
        row: int,
        column: int,
    ) -> float:
        """
        Temporarily place a candidate so its completed-junction
        score can be measured before the real search attempt.
        """

        position = grid_index(
            row,
            column,
            n,
        )

        type_id = candidate_key[0]

        if remaining_inventory[type_id] <= 0:
            return float("-inf")

        base_score = combined_candidate_score(
            candidate_key=candidate_key,
            row=row,
            column=column,
            n=n,
            candidates=candidates,
            discrepancy=discrepancy,
            statistics=frequency_statistics,
        )

        rarity_score = candidate_rarity[candidate_key]

        neighbor_score = learned_neighbor_score(
            grid=grid,
            row=row,
            column=column,
            n=n,
            candidate_key=candidate_key,
            candidates=candidates,
            frequency_statistics=frequency_statistics,
        )

        if not use_frequency_scoring:
            return base_score + 2.0 * rarity_score

        grid[position] = candidate_key
        remaining_inventory[type_id] -= 1

        junction_score = learned_junction_score(
            grid=grid,
            row=row,
            column=column,
            n=n,
            candidates=candidates,
            frequency_statistics=frequency_statistics,
        )

        remaining_inventory[type_id] += 1
        grid[position] = None

        return (
            base_score
            + 2.0 * rarity_score
            + 1.0 * neighbor_score
            + 0.25 * junction_score
        )

    search_started_at = time.perf_counter()

    def search() -> bool:
        """
        Recursive most-constrained-position search.

        Returns True when the requested solution limit has
        been reached and all further searching should stop.
        """

        nonlocal solution_count

        statistics["recursive_calls"] += 1

        if (
            SEARCH_HEARTBEAT_INTERVAL is not None
            and statistics["recursive_calls"]
            % SEARCH_HEARTBEAT_INTERVAL
            == 0
        ):
            elapsed = (
                time.perf_counter()
                - search_started_at
            )

            print(
                f"Still searching | "
                f"time: {elapsed:.1f}s | "
                f"calls: {statistics['recursive_calls']:,} | "
                f"solutions: {solution_count:,} | "
                f"attempts: {statistics['candidate_attempts']:,}"
            )

        next_choice = choose_next_position(
            grid=grid,
            n=n,
            all_candidate_keys=all_candidate_keys,
            compatibility=compatibility,
            remaining_inventory=remaining_inventory,
        )

        # No empty positions remain.

        if next_choice is None:
            solution_count += 1

            # Only retain a limited number of full boards.
            if len(solutions) < MAX_STORED_SOLUTIONS:
                solutions.append(
                    list(grid)
                )

            if (
                SOLUTION_PROGRESS_INTERVAL is not None
                and solution_count % SOLUTION_PROGRESS_INTERVAL == 0
            ):
                elapsed = (
                    time.perf_counter()
                    - search_started_at
                )

                print(
                    f"Progress: {solution_count:,} solutions found | "
                    f"time: {elapsed:.1f} seconds"
                )

            if solution_count >= max_solutions:
                statistics[
                    "stopped_at_solution_limit"
                ] = True

                return True

            return False

        row, column, possible_candidates = (
            next_choice
        )

        if not possible_candidates:
            statistics["dead_ends"] += 1
            return False

        if USE_CANDIDATE_SCORING:
            possible_candidates = sorted(
                possible_candidates,
                key=lambda candidate_key: (
                    candidate_search_score(
                        candidate_key,
                        row,
                        column,
                    ),
                    -candidate_key[0],
                    -candidate_key[1],
                ),
                reverse=True,
            )
        else:
            possible_candidates = list(
                possible_candidates
            )

        position = grid_index(
            row,
            column,
            n,
        )

        found_valid_placement = False

        for candidate_key in possible_candidates:
            statistics[
                "candidate_attempts"
            ] += 1

            type_id = candidate_key[0]

            if remaining_inventory[type_id] <= 0:
                continue

            # Place candidate.
            grid[position] = candidate_key
            remaining_inventory[type_id] -= 1

            if placement_is_valid(
                grid=grid,
                row=row,
                column=column,
                n=n,
                candidates=candidates,
                corner_library=corner_library,
            ):
                found_valid_placement = True

                statistics[
                    "placements_accepted"
                ] += 1

                should_stop = search()

                if should_stop:
                    return True

            # Undo candidate.
            remaining_inventory[type_id] += 1
            grid[position] = None

            statistics[
                "backtracks"
            ] += 1

        if not found_valid_placement:
            statistics["dead_ends"] += 1

        return False

    search()

    return (
        solutions,
        solution_count,
        statistics,
    )


# ============================================================
# SOLUTION REPORT
# ============================================================

def piece_label(
    candidate_key: tuple[int, int],
) -> str:
    """
    Create a compact type-and-rotation label.
    """

    type_id, rotation_id = (
        candidate_key
    )

    return (
        f"T{type_id}/R{rotation_id}"
    )


def write_solver_report(
    n: int,
    pieces: list[list[int]],
    piece_types: list[dict],
    candidates: dict,
    solutions: list[list],
    solution_count: int,
    statistics: dict,
    global_check_result: dict,
    discrepancy: dict[int, int],
    timing: dict,
) -> Path:
    """
    Overwrite solver_report.txt with the latest solver run.
    """

    lines = [
        "N x N PUZZLE SOLVER REPORT",
        "=" * 80,
        "",
        f"Board size: {n} x {n}",
        f"Physical pieces: {len(pieces)}",
        f"Distinct piece types: {len(piece_types)}",
        (
            "Distinct type-and-rotation candidates: "
            f"{len(candidates)}"
        ),
        f"Solutions found: {solution_count}",
        f"Complete boards stored: {len(solutions)}",
        "",
        "GLOBAL CHECKS",
        "-" * 80,
        global_check_result["reason"],
        (
            "Minimum required boundary edges: "
            f"{global_check_result['minimum_boundary_edges']}"
        ),
        (
            "Available boundary edges: "
            f"{global_check_result['available_boundary_edges']}"
        ),
        "",
        "SEARCH STATISTICS",
        "-" * 80,
        (
            "Recursive calls: "
            f"{statistics['recursive_calls']}"
        ),
        (
            "Candidate attempts: "
            f"{statistics['candidate_attempts']}"
        ),
        (
            "Accepted partial placements: "
            f"{statistics['placements_accepted']}"
        ),
        (
            "Backtracks: "
            f"{statistics['backtracks']}"
        ),
        (
            "Dead ends: "
            f"{statistics['dead_ends']}"
        ),
        "",
        "TIMING",
        "-" * 80,
        (
            "Preprocessing time: "
            f"{timing['preprocessing']:.6f} seconds"
        ),
        (
            "Search time: "
            f"{timing['search']:.6f} seconds"
        ),
        (
            "Total computation time: "
            f"{timing['total']:.6f} seconds"
        ),
        "",
        "BOUNDARY PRIORITY DATA",
        "-" * 80,
    ]

    lines.extend(
        describe_discrepancy(
            discrepancy
        )
    )

    lines.extend([
        "",
        (
            "Boundary and frequency values were used "
            "only to order candidate placements."
        ),
        (
            "They were not used to reject otherwise "
            "valid placements."
        ),
    ])

    if not solutions:
        lines.extend([
            "",
            "=" * 80,
            "NO SOLUTION WAS FOUND",
            "",
        ])
    elif solution_count > len(solutions):
        lines.extend([
            "",
            (
                f"Only {len(solutions)} complete board(s) were "
                f"stored to reduce memory and report-writing time."
            ),
        ])

    for solution_number, solution in enumerate(
        solutions[:MAX_DETAILED_REPORT_SOLUTIONS],
        start=1,
    ):
        lines.extend([
            "",
            "=" * 80,
            f"SOLUTION {solution_number}",
            "=" * 80,
            "",
            "TYPE / ROTATION GRID",
            "-" * 80,
        ])

        for row in range(n):
            labels = []

            for column in range(n):
                key = solution[
                    grid_index(
                        row,
                        column,
                        n,
                    )
                ]

                labels.append(
                    piece_label(key)
                )

            lines.append(
                " | ".join(labels)
            )

        lines.extend([
            "",
            "DETAILED PLACEMENTS",
            "-" * 80,
        ])

        for row in range(n):
            for column in range(n):
                position = grid_index(
                    row,
                    column,
                    n,
                )

                candidate_key = solution[
                    position
                ]

                candidate = candidates[
                    candidate_key
                ]

                lines.extend([
                    (
                        f"Position "
                        f"({row + 1}, {column + 1})"
                    ),
                    (
                        f"  Piece type: "
                        f"{candidate['type_id']}"
                    ),
                    (
                        f"  Rotation: "
                        f"{candidate['rotation_id']}"
                    ),
                    (
                        "  Edges "
                        "[top, right, bottom, left]: "
                        f"{list(candidate['edges'])}"
                    ),
                    (
                        "  Corners "
                        "[top-left, top-right, "
                        "bottom-right, bottom-left]: "
                        f"{list(candidate['corners'])}"
                    ),
                    "",
                ])

        lines.extend([
            "COMPLETED INTERNAL JUNCTIONS",
            "-" * 80,
        ])

        for row in range(1, n):
            for column in range(1, n):
                junction = completed_junction(
                    grid=solution,
                    row=row,
                    column=column,
                    n=n,
                    candidates=candidates,
                )

                lines.append(
                    f"Junction at grid crossing "
                    f"({row}, {column}): "
                    f"{list(junction)}"
                )

    lines.extend([
        "",
        "=" * 80,
        "END OF REPORT",
        "",
    ])

    with SOLUTION_REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "\n".join(lines)
        )

    return SOLUTION_REPORT_FILE


# ============================================================
# REPORT DELETION
# ============================================================

def ask_whether_to_delete_report(
    report_file: Path,
) -> None:
    """
    Delete the report only after explicit confirmation.
    """

    answer = input(
        "\nDelete the report file now? "
        "Enter y to delete it, "
        "or press Enter to keep it: "
    ).strip().lower()

    if answer in {
        "y",
        "yes",
    }:
        try:
            report_file.unlink()
            print("Report file deleted.")

        except FileNotFoundError:
            print(
                "The report file was already absent."
            )

    else:
        print("Report file kept.")


# ============================================================
# MAIN PROGRAM
# ============================================================

def main() -> None:
    program_start_time = (
        time.perf_counter()
    )

    try:
        pieces = get_piece_input()

    except ValueError as error:
        print(
            f"\nInput error: {error}"
        )
        return

    preprocessing_start_time = (
        time.perf_counter()
    )

    global_check_result = (
        run_global_checks(
            pieces
        )
    )

    if not global_check_result["possible"]:
        print("\nNO SOLUTION")
        print(
            global_check_result["reason"]
        )
        return

    n = determine_board_size(
        len(pieces)
    )

    discrepancy = (
        calculate_symbol_discrepancy(
            pieces
        )
    )

    frequency_statistics = (
        load_statistics()
    )

    piece_types = build_piece_types(
        pieces
    )

    initial_inventory = (
        create_piece_inventory(
            piece_types
        )
    )

    try:
        prepared = prepare_compatibility(
            piece_types
        )

        # Loaded for compatibility with the existing project.
        # It is not currently used as a hard validity rule.
        corner_library = (
            load_corner_library()
        )

    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        AssertionError,
    ) as error:
        print(
            f"\nPreparation error:\n{error}"
        )
        return

    candidates = prepared[
        "candidates"
    ]

    compatibility = prepared[
        "compatibility"
    ]

    preprocessing_end_time = (
        time.perf_counter()
    )

    search_start_time = (
        time.perf_counter()
    )

    solutions, solution_count, statistics = solve_puzzle(
        n=n,
        piece_types=piece_types,
        candidates=candidates,
        compatibility=compatibility,
        corner_library=corner_library,
        initial_inventory=initial_inventory,
        discrepancy=discrepancy,
        frequency_statistics=frequency_statistics,
        max_solutions=MAX_SOLUTIONS,
    )

    search_end_time = (
        time.perf_counter()
    )

    timing = {
        "preprocessing": (
            preprocessing_end_time
            - preprocessing_start_time
        ),
        "search": (
            search_end_time
            - search_start_time
        ),
        "total": (
            search_end_time
            - preprocessing_start_time
        ),
        "program_total": (
            search_end_time
            - program_start_time
        ),
    }

    frequency_report_file = None

    if solutions:
        updated_statistics = (
            record_solution_statistics(
                solution=solutions[0],
                n=n,
                candidates=candidates,
            )
        )

        frequency_report_file = (
            write_frequency_report(
                updated_statistics
            )
        )

    report_file = write_solver_report(
        n=n,
        pieces=pieces,
        piece_types=piece_types,
        candidates=candidates,
        solutions=solutions,
        solution_count=solution_count,
        statistics=statistics,
        global_check_result=global_check_result,
        discrepancy=discrepancy,
        timing=timing,
    )

    print("\nSolver finished.")
    print(f"Board size: {n} x {n}")
    print(
        f"Solutions found: "
        f"{solution_count:,}"
    )

    if statistics["stopped_at_solution_limit"]:
        print(
            f"Search stopped after reaching the "
            f"{MAX_SOLUTIONS:,}-solution limit."
        )
        print(
            f"The puzzle has at least "
            f"{solution_count:,} solutions."
        )
    else:
        print(
            "The complete search space was exhausted."
        )
        print(
            f"Exact total solutions: "
            f"{solution_count:,}"
        )


    print(
        f"Search time: "
        f"{timing['search']:.6f} seconds"
    )
    print(
        f"Total computation time: "
        f"{timing['total']:.6f} seconds"
    )
    print(
        f"Candidate attempts: "
        f"{statistics['candidate_attempts']}"
    )
    print(
        f"Backtracks: "
        f"{statistics['backtracks']}"
    )
    print(
        f"Dead ends: "
        f"{statistics['dead_ends']}"
    )
    print(
        f"\nDetailed report written to:\n"
        f"{report_file}"
    )

    if frequency_report_file is not None:
        print(
            "\nFrequency statistics updated:"
        )
        print(
            frequency_report_file
        )

    ask_whether_to_delete_report(
        report_file
    )


if __name__ == "__main__":
    main()