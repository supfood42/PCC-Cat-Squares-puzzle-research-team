import numpy as np
import sys
import os
import catPuzzleHandling as surgeon
# Since the function only returns one thing, we only need one variable here!
puzzleData, n, numPuzzles = surgeon.load_puzzles()
#initialize a 4D array to represent all possible boards where the puzzle is going to be solved
num_cases = 4 * n * n
solvingArray = np.zeros((num_cases, n, n, 4), dtype=int)

for i in range(numPuzzles):
    #load puzzle data for this loop
    initialBoard = puzzleData[i]

    # 1. Reshape all n x n pieces into shape (n*n, 4)
    base_pieces = initialBoard.reshape(n * n, 4)

    # 2. Generate all 4 rotations for every piece using np.roll along axis 1
    # np.roll shifts side values: [A, B, C, D] -> [D, A, B, C]
    rotations = [np.roll(base_pieces, shift=k, axis=1) for k in range(4)]

    # 3. Stack all 4 rotated variations into a single array of shape (4 * n * n, 4)
    all_rotated_pieces = np.vstack(rotations)

    

    # 5. Assign all piece/rotation variations to position (0, 0) across all boards
    solvingArray[:, 0, 0] = all_rotated_pieces