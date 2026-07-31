import numpy as np
import sys
import os
import tkinter as tk
from tkinter import filedialog

def load_puzzles():
    """
    Opens a file dialog to select a puzzle file, parses dimensions, 
    and uses NumPy's loadtxt to load and reshape the puzzle array efficiently.
    """
    # 1. Initialize hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()

    # 2. Open the file dialog
    file_path = filedialog.askopenfilename(
        title="Select a Puzzle File",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )

    if not file_path:
        print("No file selected. Exiting...")
        sys.exit(0)

    # 3. Extract parameters from filename
    filename = os.path.basename(file_path)
    try:
        name_parts = filename.replace('.txt', '').split('_')
        n = int(name_parts[1].split('x')[0])
        numPuzzles = int(name_parts[2])
    except (IndexError, ValueError):
        print(f"Error: Filename '{filename}' format must be 'name_NxN_puzzles.txt'.")
        sys.exit(1)

    # 4. Load all pieces at once and reshape into 4D numpy array
    try:
        # Load entire text file as integers
        raw_data = np.loadtxt(file_path, dtype=int)
        
        # Reshape directly into (numPuzzles, n, n, 4)
        puzzleData = raw_data.reshape((numPuzzles, n, n, 4))
        
        print(f"Successfully loaded {numPuzzles} puzzles of size {n}x{n} from '{filename}'.")
        return puzzleData, n, numPuzzles

    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        sys.exit(1)

import time

def start_timer():
    """
    Starts the timer and returns the current high-resolution timestamp.
    """
    return time.perf_counter()


def report_time(start_time, num_puzzles):
    """
    Calculates time stats and returns a list containing:
    [total_time_ms, num_puzzles, avg_time_per_puzzle_ms]
    """
    end_time = time.perf_counter()
    
    total_time_ms = (end_time - start_time) * 1000
    avg_time_ms = total_time_ms / num_puzzles
    
    return [total_time_ms, num_puzzles, avg_time_ms]

def rotate_piece(piece):
    #rotates puzzle piece clockwise
    return [piece[3], piece[0], piece[1], piece[2]]

def rotate_piece_inBits(piece):
    #Rotate packed [Top][Right][Bottom][Left] clockwise once.
    piece = int(piece) & 0xFFFF
    return np.uint16((piece >> 4) | ((piece & 0xF) << 12))

'''
def pick_random_piece_fromBoard(board):
    recieves a single board and picks a random piece from it, reporting it's coordinates for extermination.
    If the piece is empty ([0,0,0,0] then it picks another one)
    n = board.shape[0]
    while True:
        # Pick random row and column indices in the range [0, n-1]
        r = np.random.randint(0, n)
        c = np.random.randint(0, n)

        # Retrieve the piece (vector of length 4) at (r, c)
        piece = board[r, c]

        # Check if the piece is NOT empty [0, 0, 0, 0]
        if not np.array_equal(piece, [0, 0, 0, 0]):
            return piece, r, c
'''

def pick_random_piece_fromList(available_pieces):
    """Picks a random piece from available_pieces and removes it using Swap-and-Pop.

    Returns the picked piece and the updated array of remaining pieces.
    """
    num_remaining = len(available_pieces)

    # 1. Pick a random index from what's left
    idx = np.random.randint(0, num_remaining)
    picked_piece = available_pieces[idx].copy()

    # 2. Swap picked piece with the last element
    available_pieces[idx] = available_pieces[-1]

    # 3. Pop the last element by trimming the slice by 1
    remaining_pieces = available_pieces[:-1]

    return picked_piece, remaining_pieces

def swap_pop(
    available_pieces: np.ndarray,
    index: int,
) -> np.ndarray:
    """
    Remove one piece without preserving array order.

    The last piece replaces the removed piece, and the active
    array view is shortened by one element.
    """
    available_pieces[index] = available_pieces[-1]

    return available_pieces[:-1]

#--------Code that converts row-number into the more superawesome bit form
# Negative edges get single 1-bits; Positive edges get their exact bitwise inverses.
EDGE_TO_BIT = {
    -1: 0b1000,  # 8
    -2: 0b0100,  # 4
    -3: 0b0010,  # 2
    -4: 0b0001,  # 1
    +1: 0b0111,  # 7
    +2: 0b1011,  # 11
    +3: 0b1101,  # 13
    +4: 0b1110,  # 14
}

# Inverse map to convert nibbles back to original signed integers
BIT_TO_EDGE = {v: k for k, v in EDGE_TO_BIT.items()}

def piece_to_bits(piece: np.ndarray) -> int:
    """Converts a 1D NumPy array of 4 signed edges into a packed 16-bit integer."""
    top = EDGE_TO_BIT[int(piece[0])]
    right = EDGE_TO_BIT[int(piece[1])]
    bottom = EDGE_TO_BIT[int(piece[2])]
    left = EDGE_TO_BIT[int(piece[3])]

    # Shift each 4-bit nibble into position:
    # [Top (bits 12-15)] [Right (bits 8-11)] [Bottom (bits 4-7)] [Left (bits 0-3)]
    packed_16bit = (top << 12) | (right << 8) | (bottom << 4) | left

    return packed_16bit

def bits_to_piece(packed_16bit: int) -> np.ndarray:
    """Extracts a 16-bit packed integer back into a 1D NumPy array [Top, Right, Bottom, Left]."""
    MASK = 0xF  # 0b1111 (isolates 4 bits at a time)

    top_nibble = (packed_16bit >> 12) & MASK
    right_nibble = (packed_16bit >> 8) & MASK
    bottom_nibble = (packed_16bit >> 4) & MASK
    left_nibble = packed_16bit & MASK

    return np.array(
        [
            BIT_TO_EDGE[top_nibble],
            BIT_TO_EDGE[right_nibble],
            BIT_TO_EDGE[bottom_nibble],
            BIT_TO_EDGE[left_nibble],
        ],
        dtype=int,
    )

def board_to_bits_vector(board: np.ndarray) -> np.ndarray:
    """Dissects a 3D board array (n, n, 4) into a 1D NumPy vector of 16-bit packed integers

    in left-to-right, top-to-bottom order.
    """
    n = board.shape[0]

    # Reshape (n, n, 4) into a 2D array of pieces (n*n, 4)
    # NumPy's default reshaping operates row-by-row (left-to-right, top-down)
    flat_pieces = board.reshape(n * n, 4)

    # Convert each 4-element piece vector to its packed 16-bit integer
    vector_1d = np.array(
        [piece_to_bits(p) for p in flat_pieces], dtype=np.uint16
    )

    return vector_1d

def bits_vector_to_board(vector_1d: np.ndarray, n: int) -> np.ndarray:
    """Reconstructs an (n, n, 4) 3D board array from a 1D vector of packed 16-bit integers."""
    # Unpack each 16-bit int into a [4] array -> results in shape (n*n, 4)
    flat_pieces = np.array([bits_to_piece(b) for b in vector_1d], dtype=int)

    # Reshape back to 3D grid layout (n, n, 4)
    return flat_pieces.reshape(n, n, 4)

