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
        return puzzleData

    except Exception as e:
        print(f"Error reading file '{filename}': {e}")
        sys.exit(1)


# Execution check
if __name__ == "__main__":
    puzzleData = load_puzzles()