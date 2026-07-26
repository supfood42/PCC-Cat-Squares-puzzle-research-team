from collections import Counter


def get_unfilled_boundary_sides(
    grid: list,
    n: int,
) -> list[tuple[int, int, int]]:
    """
    Return every unfilled outward-facing board edge.

    Each result is:
        (row, column, edge_index)

    Edge indexes:
        0 = top
        1 = right
        2 = bottom
        3 = left
    """

    sides = []

    for row in range(n):
        for column in range(n):
            position = row * n + column

            if grid[position] is not None:
                continue

            if row == 0:
                sides.append((row, column, 0))

            if column == n - 1:
                sides.append((row, column, 1))

            if row == n - 1:
                sides.append((row, column, 2))

            if column == 0:
                sides.append((row, column, 3))

    return sides


def current_exposed_boundary_counts(
    grid: list,
    n: int,
    candidates: dict,
) -> Counter:
    """
    Count signed edges already exposed on the outer boundary.
    """

    counts = Counter()

    for row in range(n):
        for column in range(n):
            position = row * n + column
            candidate_key = grid[position]

            if candidate_key is None:
                continue

            edges = candidates[candidate_key]["edges"]

            if row == 0:
                counts[edges[0]] += 1

            if column == n - 1:
                counts[edges[1]] += 1

            if row == n - 1:
                counts[edges[2]] += 1

            if column == 0:
                counts[edges[3]] += 1

    return counts


def required_final_boundary_discrepancy(
    original_discrepancy: dict[int, int],
) -> dict[int, int]:
    """
    In any complete solution, the signed difference on the
    boundary must equal the puzzle's total signed difference,
    because all internal matches cancel.
    """

    return dict(original_discrepancy)


def remaining_boundary_requirements(
    grid: list,
    n: int,
    candidates: dict,
    original_discrepancy: dict[int, int],
) -> dict[int, int]:
    """
    Calculate the additional signed discrepancy that still must
    be supplied by unfilled boundary positions.

    Positive:
        more heads of this color must remain exposed.

    Negative:
        more bodies of this color must remain exposed.
    """

    exposed = current_exposed_boundary_counts(
        grid=grid,
        n=n,
        candidates=candidates,
    )

    requirements = {}

    for color in range(1, 5):
        current_difference = (
            exposed[color]
            - exposed[-color]
        )

        requirements[color] = (
            original_discrepancy[color]
            - current_difference
        )

    return requirements


def maximum_possible_symbol_exposure(
    remaining_inventory: dict[int, int],
    piece_types_by_id: dict[int, dict],
    color: int,
    sign: int,
) -> int:
    """
    Return an optimistic upper bound for how many copies of one
    signed symbol the remaining pieces could expose.

    sign:
         1 means heads
        -1 means bodies

    This intentionally overestimates what is achievable.
    Therefore, it is safe for rejection.
    """

    target = sign * color
    maximum = 0

    for type_id, remaining_count in remaining_inventory.items():
        if remaining_count <= 0:
            continue

        piece_type = piece_types_by_id[type_id]

        best_exposure_per_copy = 0

        for rotation in piece_type["rotations"]:
            occurrence_count = rotation["edges"].count(
                target
            )

            best_exposure_per_copy = max(
                best_exposure_per_copy,
                occurrence_count,
            )

        maximum += (
            remaining_count
            * best_exposure_per_copy
        )

    return maximum


def boundary_inventory_is_feasible(
    grid: list,
    n: int,
    candidates: dict,
    remaining_inventory: dict[int, int],
    piece_types_by_id: dict[int, dict],
    original_discrepancy: dict[int, int],
) -> bool:
    """
    Reject when the unused pieces cannot possibly supply the
    signed boundary discrepancy still required.

    Passing this test does not prove the branch is solvable.
    Failing it proves the branch is impossible.
    """

    unfilled_boundary_sides = get_unfilled_boundary_sides(
        grid=grid,
        n=n,
    )

    number_of_open_sides = len(
        unfilled_boundary_sides
    )

    requirements = remaining_boundary_requirements(
        grid=grid,
        n=n,
        candidates=candidates,
        original_discrepancy=original_discrepancy,
    )

    minimum_required_sides = sum(
        abs(value)
        for value in requirements.values()
    )

    if minimum_required_sides > number_of_open_sides:
        return False

    for color in range(1, 5):
        requirement = requirements[color]

        if requirement > 0:
            maximum_heads = maximum_possible_symbol_exposure(
                remaining_inventory=remaining_inventory,
                piece_types_by_id=piece_types_by_id,
                color=color,
                sign=1,
            )

            if maximum_heads < requirement:
                return False

        elif requirement < 0:
            maximum_bodies = maximum_possible_symbol_exposure(
                remaining_inventory=remaining_inventory,
                piece_types_by_id=piece_types_by_id,
                color=color,
                sign=-1,
            )

            if maximum_bodies < abs(requirement):
                return False

    return True