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
# Fie load check
if __name__ == "__main__":
    puzzleData = load_puzzles()