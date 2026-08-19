import numpy as np
from collections import deque

import time

import catPuzzleHandling as surgeon
import BFS_functions as BFS

puzzleData, n, numPuzzles = surgeon.load_puzzles()
total_start_time = time.perf_counter()
total_solutions = 0

for puzzle_index in range(numPuzzles):
    puzzle_start_time = time.perf_counter()
    initialBoard = puzzleData[puzzle_index]
    vectored_board = surgeon.board_to_bits_vector(initialBoard)
    lookup = BFS.build_lookup(vectored_board)
    queue = deque()

    for startCase in range(n*n*4):
        available_mask = np.ones(n*n, dtype = bool)
        solvingBoard = np.zeros((n, n), dtype=np.uint16)
        startingPiece_idx = startCase // 4
        startingPiece_numRotation = startCase % 4

        startingPiece = vectored_board[startingPiece_idx]

        for rotation in range(startingPiece_numRotation):
            startingPiece = surgeon.rotate_piece_inBits(startingPiece)
        solvingBoard[0,0] = startingPiece

        available_mask[startingPiece_idx] = False
        queue.append(
            (solvingBoard, available_mask)
        )

    numberOfLayers = (2*n) - 2
    for layer in range(numberOfLayers):
        numberOfParents = len(queue)
        for parent in range(numberOfParents):
            solvingBoard, available_mask = queue.popleft()
            children = BFS.compute_layer(
            solvingBoard,
            available_mask,
            lookup,
            )
            queue.extend(children)

    puzzle_end_time = time.perf_counter()
    solving_time = puzzle_end_time - puzzle_start_time
    number_of_solutions = len(queue)
    total_solutions += number_of_solutions

    print(
        f"Puzzle {puzzle_index + 1}: "
        f"{number_of_solutions} solutions found in "
        f"{solving_time:.6f} seconds"
    )

total_time = time.perf_counter() - total_start_time
average_time_per_puzzle = total_time / numPuzzles if numPuzzles else 0
time_per_solution = total_time / total_solutions if total_solutions else 0
average_solutions_per_puzzle = total_solutions / numPuzzles if numPuzzles else 0

print(
    f"Total time: {total_time:.6f} seconds\n"
    f"Time/puzzle: {average_time_per_puzzle:.6f} seconds\n"
    f"Total solutions: {total_solutions}\n"
    f"Average solutions/puzzle: {average_solutions_per_puzzle:.6f}\n"
    f"Time/solution: {time_per_solution:.6f} seconds"
)