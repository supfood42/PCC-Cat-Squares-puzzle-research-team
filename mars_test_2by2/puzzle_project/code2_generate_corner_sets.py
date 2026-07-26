import json
from pathlib import Path

VALUE_ORDER = [1, 2, 3, 4, -1, -2, -3, -4]
VALUE_TO_INDEX = {value: index for index, value in enumerate(VALUE_ORDER)}

OUTPUT_FILE = Path("unique_valid_corner_sets.json")


def pair_to_id(first, second):
    """Convert [first, second] into an ID from 1 to 64."""
    return (
        VALUE_TO_INDEX[first] * 8
        + VALUE_TO_INDEX[second]
        + 1
    )


def id_to_pair(corner_id):
    """Convert an ID from 1 to 64 back into [first, second]."""
    position = corner_id - 1

    return [
        VALUE_ORDER[position // 8],
        VALUE_ORDER[position % 8],
    ]


def complete_set(first_id, second_id):
    """
    A = [a, b]
    B = [c, d]
    C = [-b, -c]
    D = [-d, -a]
    """

    a, b = id_to_pair(first_id)
    c, d = id_to_pair(second_id)

    third_id = pair_to_id(-b, -c)
    fourth_id = pair_to_id(-d, -a)

    return [
        first_id,
        second_id,
        third_id,
        fourth_id,
    ]


def canonical_rotation(corners):
    """
    Treat all rotations of a square as the same set.

    Example:
        [64, 22, 33, 17]
        [22, 33, 17, 64]
        [33, 17, 64, 22]
        [17, 64, 22, 33]

    All become:
        (17, 64, 22, 33)
    """

    rotations = [
        tuple(corners[i:] + corners[:i])
        for i in range(4)
    ]

    return min(rotations)


def generate_unique_sets():
    """Generate valid sets and remove rotational duplicates."""

    unique_sets = set()

    for first_id in range(1, 65):
        for second_id in range(1, 65):
            corners = complete_set(first_id, second_id)
            unique_sets.add(canonical_rotation(corners))

    return sorted(unique_sets)


def save_sets(valid_sets):
    """Save the sets permanently as a JSON file."""

    data = {
        "value_order": VALUE_ORDER,
        "rotations_count_as_same": True,
        "number_of_sets": len(valid_sets),
        "valid_sets": [list(item) for item in valid_sets],
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def load_sets():
    """Load the previously saved sets."""

    with OUTPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data["valid_sets"]


def save_text_file(valid_sets):
    with open(
        "unique_valid_corner_sets.txt",
        "w",
        encoding="utf-8"
    ) as file:

        for corners in valid_sets:
            file.write(str(list(corners)) + "\n")

def main():
    if OUTPUT_FILE.exists():
        print(f"Loading saved sets from: {OUTPUT_FILE.resolve()}")
        valid_sets = load_sets()
    else:
        print("Generating unique valid sets...")
        valid_sets = generate_unique_sets()

    # Save both files every time.
    save_sets(valid_sets)
    save_text_file(valid_sets)

    print(f"JSON file: {OUTPUT_FILE.resolve()}")
    print(
        "Text file:",
        Path("unique_valid_corner_sets.txt").resolve()
    )

    print(f"Number of unique sets: {len(valid_sets)}")

    print("\nFirst 10 sets:")
    for corners in valid_sets[:10]:
        print(corners)

    return valid_sets


valid_corner_sets = main()