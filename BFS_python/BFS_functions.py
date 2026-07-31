import numpy as np

def transcribe_sides(solvingBoard: np.ndarray, layer: int) -> np.ndarray:
    """
    Return a 1D NumPy array of uint8 target corners for the next diagonal.

    Each target corner has the format:

        [required top edge][required left edge]
             4 bits             4 bits

    Only positions requiring both a top-edge match and a left-edge match
    are included. The one-sided topmost and leftmost boundary positions
    are handled separately by the main algorithm.

    The pieces in the current diagonal are read from bottom-left to
    top-right.
    I know it looks and smells like AI but i was too lazy to write the comments
    """
    n = solvingBoard.shape[0]

    # Coordinates of the current diagonal, ordered bottom-left to top-right.
    min_col = max(0, layer - n + 1)
    max_col = min(layer, n - 1)

    cols = np.arange(min_col, max_col + 1)
    rows = layer - cols

    # Packed pieces use:
    # [Top][Right][Bottom][Left]
    pieces = solvingBoard[rows, cols].astype(np.uint16, copy=False)

    # Obtain the edges that face the next diagonal.
    right_edges = ((pieces >> 8) & 0x0F).astype(np.uint8)
    bottom_edges = ((pieces >> 4) & 0x0F).astype(np.uint8)

    # A matching edge is the four-bit inverse.
    required_left = right_edges ^ np.uint8(0x0F)
    required_top = bottom_edges ^ np.uint8(0x0F)

    # Each next-diagonal interior position lies between two current pieces:
    #
    # current piece i     supplies its right edge
    # current piece i + 1 supplies its bottom edge
    #
    # Target format:
    # [inverse bottom of piece i + 1][inverse right of piece i]
    target_corners = (
        (required_top[1:] << 4)
        | required_left[:-1]
    ).astype(np.uint8)

    return target_corners

#----Matching piece Search function
#----NOTICE: This function is the most run in the entire BFS search flow, by orders of magnitude. The current iteration is never the best, but any imporvement is a lot added.
# -----------------------------------------------------------------------------
#IN:    target_corner: uint8 where first 4 bits is the top edge of desired piece
#                   last 4 bits is the left edge of the desired piece
#       available_pieces_1d: 1D array of uint16 where each element is a packed piece to choose from
#OUT:   index: index of the matching piece in available_pieces_1d, or -1 if not found
#       matching_piece: uint16 packed piece that matches the target_corner, or 16 0s if not found

from typing import Tuple

def find_matching_piece(
    target_corner: np.uint8,
    available_pieces_1d: np.ndarray,
) -> Tuple[int, np.uint16]:
    
    pieces = np.asarray(available_pieces_1d, dtype=np.uint16)

    if pieces.size == 0:
        return -1, np.uint16(0)

    target_corner = np.uint8(target_corner)

    target_top = (target_corner >> 4) & np.uint8(0x0F)
    target_left = target_corner & np.uint8(0x0F)

    # Use uint32 while shifting to prevent overflow during intermediate steps.
    pieces32 = pieces.astype(np.uint32)

    # Packed format is [Top][Right][Bottom][Left].
    #
    # Clockwise rotations:
    # 0 turns: [T][R][B][L]
    # 1 turn : [L][T][R][B]
    # 2 turns: [B][L][T][R]
    # 3 turns: [R][B][L][T]
    rotated_0 = pieces32

    rotated_1 = (
        (pieces32 >> 4)
        | ((pieces32 & 0x000F) << 12)
    )

    rotated_2 = (
        (pieces32 >> 8)
        | ((pieces32 & 0x00FF) << 8)
    )

    rotated_3 = (
        (pieces32 >> 12)
        | ((pieces32 & 0x0FFF) << 4)
    )

    rotations = np.stack(
        [rotated_0, rotated_1, rotated_2, rotated_3],
        axis=1,
    )

    # Extract the top and left nibble of every rotated orientation.
    tops = (rotations >> 12) & 0x0F
    lefts = rotations & 0x0F

    matches = (
        (tops == np.uint32(target_top))
        & (lefts == np.uint32(target_left))
    )

    # Find which original pieces match in at least one orientation.
    matching_piece_rows = np.any(matches, axis=1)

    if not np.any(matching_piece_rows):
        return -1, np.uint16(0)

    # Select the first matching piece in available_pieces_1d.
    index = int(np.argmax(matching_piece_rows))

    # Select its first matching orientation:
    # original, then 90°, 180°, and 270° clockwise.
    rotation_index = int(np.argmax(matches[index]))

    matching_piece = np.uint16(rotations[index, rotation_index])

    return index, matching_piece





'''For new BFS code that uses queue
Made by chatgpt@tm so def improve later'''

import numpy as np
import catPuzzleHandling as surgeon


def compute_layer(
    solvingBoard: np.ndarray,
    available_mask: np.ndarray,
    vectored_board: np.ndarray,
):
    """
    Fill the next empty diagonal in every possible way.

    Returns a list of children:
        [(child_board, child_mask), ...]
    """
    n = solvingBoard.shape[0]

    # Find the first diagonal that has not been filled.
    next_layer = None

    for layer in range(2 * n - 1):
        min_col = max(0, layer - n + 1)
        max_col = min(layer, n - 1)

        cols = np.arange(min_col, max_col + 1)
        rows = layer - cols

        if np.any(solvingBoard[rows, cols] == 0):
            next_layer = layer
            break

    if next_layer is None:
        return []

    # Coordinates of the next diagonal, bottom-left to top-right.
    min_col = max(0, next_layer - n + 1)
    max_col = min(next_layer, n - 1)

    coordinates = [
        (next_layer - col, col)
        for col in range(min_col, max_col + 1)
    ]

    # Calculate the required top and left edge for each position.
    target_corners = []

    for row, col in coordinates:
        required_top = 0
        required_left = 0

        if row > 0:
            piece_above = int(solvingBoard[row - 1, col])
            bottom_edge = (piece_above >> 4) & 0x0F
            required_top = bottom_edge ^ 0x0F

        if col > 0:
            piece_left = int(solvingBoard[row, col - 1])
            right_edge = (piece_left >> 8) & 0x0F
            required_left = right_edge ^ 0x0F

        target_corner = np.uint8(
            (required_top << 4) | required_left
        )

        target_corners.append(target_corner)

    children = []

    # Use one working copy and backtrack through every possibility.
    working_board = solvingBoard.copy()
    working_mask = available_mask.copy()

    def fill_position(position_index):
        # The entire diagonal has been filled.
        if position_index == len(coordinates):
            children.append(
                (
                    working_board.copy(),
                    working_mask.copy(),
                )
            )
            return

        row, col = coordinates[position_index]
        target_corner = int(target_corners[position_index])

        target_top = (target_corner >> 4) & 0x0F
        target_left = target_corner & 0x0F

        # Every True index represents one available physical piece.
        for piece_index in np.flatnonzero(working_mask):
            rotated_piece = np.uint16(
                vectored_board[piece_index]
            )

            # Test all four rotations separately.
            for _ in range(4):
                packed_piece = int(rotated_piece)

                piece_top = (packed_piece >> 12) & 0x0F
                piece_left = packed_piece & 0x0F

                top_matches = (
                    target_top == 0
                    or piece_top == target_top
                )

                left_matches = (
                    target_left == 0
                    or piece_left == target_left
                )

                if top_matches and left_matches:
                    working_board[row, col] = rotated_piece
                    working_mask[piece_index] = False

                    fill_position(position_index + 1)

                    # Undo this placement before trying another branch.
                    working_mask[piece_index] = True
                    working_board[row, col] = np.uint16(0)

                rotated_piece = surgeon.rotate_piece_inBits(
                    rotated_piece
                )

    fill_position(0)

    return children