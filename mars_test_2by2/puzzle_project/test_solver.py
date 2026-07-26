from collections import Counter

from puzzle_checks import (
    determine_board_size,
    run_global_checks,
)

from piece_types import (
    build_piece_types,
    create_piece_inventory,
)

from compatibility import prepare_compatibility

from scoring import calculate_symbol_discrepancy

from frequency_stats import empty_statistics

from solver import solve_puzzle


def run_solver_for_test(
    pieces: list[list[int]],
    max_solutions: int = 100,
):
    """
    Prepare and solve a puzzle without terminal input,
    reports, or saved frequency updates.
    """

    global_result = run_global_checks(pieces)

    assert global_result["possible"], (
        global_result["reason"]
    )

    n = determine_board_size(len(pieces))

    piece_types = build_piece_types(pieces)
    inventory = create_piece_inventory(piece_types)

    prepared = prepare_compatibility(piece_types)

    discrepancy = calculate_symbol_discrepancy(
        pieces
    )

    # The corner library is not used by placement_is_valid,
    # so an empty placeholder is enough for testing.
    corner_library = {
        "oriented_sets": set(),
    }

    solutions, statistics = solve_puzzle(
        n=n,
        piece_types=piece_types,
        candidates=prepared["candidates"],
        compatibility=prepared["compatibility"],
        corner_library=corner_library,
        initial_inventory=inventory,
        discrepancy=discrepancy,
        frequency_statistics=empty_statistics(),
        max_solutions=max_solutions,
    )

    return solutions, statistics


def assert_solution_edges_match(
    solution: list,
    n: int,
    candidates: dict,
) -> None:
    """
    Independently verify every internal edge in one solution.
    """

    for row in range(n):
        for column in range(n):
            position = row * n + column
            current = candidates[solution[position]]
            top, right, bottom, left = current["edges"]

            if column < n - 1:
                neighbor = candidates[
                    solution[position + 1]
                ]

                neighbor_left = neighbor["edges"][3]

                assert right == -neighbor_left

            if row < n - 1:
                neighbor = candidates[
                    solution[position + n]
                ]

                neighbor_top = neighbor["edges"][0]

                assert bottom == -neighbor_top


def test_known_2x2() -> None:
    pieces = [
        [-2, 4, -2, -4],
        [-2, -2, -1, 2],
        [-4, -4, -1, -2],
        [2, 2, 2, 3],
    ]

    solutions, statistics = run_solver_for_test(
        pieces,
        max_solutions=100,
    )

    assert len(solutions) == 8, (
        f"Expected 8 solutions, got "
        f"{len(solutions)}"
    )

    piece_types = build_piece_types(pieces)
    prepared = prepare_compatibility(piece_types)

    for solution in solutions:
        assert_solution_edges_match(
            solution=solution,
            n=2,
            candidates=prepared["candidates"],
        )

    print("PASS: known 2 x 2 puzzle")
    print(f"Solutions: {len(solutions)}")
    print(
        "Candidate attempts: "
        f"{statistics['candidate_attempts']}"
    )


def test_impossible_2x2() -> None:
    pieces = [
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1],
        [1, 1, 1, 1],
    ]

    global_result = run_global_checks(pieces)

    assert not global_result["possible"]

    print("PASS: impossible 2 x 2 rejected")

def test_known_3x3() -> None:
    pieces = [
        [4, -2, -2, -1],
        [-4, 3, -4, 4],
        [2, -3, 2, -2],
        [-3, -3, -1, 4],
        [-2, -3, 2, 1],
        [-4, 4, 1, 3],
        [-1, 3, 2, 1],
        [-2, -4, 3, -1],
        [-2, -1, -2, -4],
    ]

    solutions, statistics = run_solver_for_test(
        pieces,
        max_solutions=1,
    )

    assert len(solutions) >= 1, (
        "Expected the known 3 x 3 puzzle "
        "to have a solution."
    )

    piece_types = build_piece_types(pieces)
    prepared = prepare_compatibility(piece_types)

    assert_solution_edges_match(
        solution=solutions[0],
        n=3,
        candidates=prepared["candidates"],
    )

    print("PASS: known 3 x 3 puzzle")
    print(
        "Candidate attempts: "
        f"{statistics['candidate_attempts']}"
    )

def main() -> None:
    test_known_2x2()
    test_impossible_2x2()
    test_known_3x3()

    print()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()