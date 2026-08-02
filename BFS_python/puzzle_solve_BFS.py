import numpy as np
from collections import deque

import time

import catPuzzleHandling as surgeon
import BFS_functions as BFS

#Config
REPORT_INTERVAL = 10.0 #seconds
#Move this to BFS functions later
def decode_solution(packed_board):
    """
    Convert an n x n packed-bit board into an n x n x 4 array.

    Final edge order:
        [Top, Right, Bottom, Left]
    """
    board_size = packed_board.shape[0]

    decoded_board = np.zeros(
        (board_size, board_size, 4),
        dtype=np.int8
    )

    for row in range(board_size):
        for column in range(board_size):
            decoded_board[row, column] = surgeon.bits_to_piece(
                packed_board[row, column]
            )

    return decoded_board


puzzleData, n, numPuzzles = surgeon.load_puzzles()

for i in range(numPuzzles):
    #Report stuff, non-crucial
    print("\n" + "=" * 70)
    print(f"Starting puzzle {i + 1} of {numPuzzles}")
    print("=" * 70)

    puzzle_start_time = time.perf_counter()
    next_report_time = (
        puzzle_start_time + REPORT_INTERVAL
    )
    #-------------
    #load puzzle data for this loop
    initialBoard = puzzleData[i]
    #vectorize board
    vectored_board = surgeon.board_to_bits_vector(initialBoard)

    #THE code
    queue = deque()
    #queue of death. destroyer of all worlds

    #For the first piece, there is no contraint so we just make n*n*4 cases
    for startCase in range(n*n*4):
        #Initializes a boolean mask for available pieces. For the starter cases it's all ones (all available)
        available_mask = np.ones(n*n, dtype = bool)
        #initiaze the solving board fro this case (2D) with zeroes
        solvingBoard = np.zeros((n, n), dtype=np.uint16)
        #Translates case number into the number of puzzle and number of rotations
        startingPiece_idx = startCase // 4
        startingPiece_numRotation = startCase % 4

        startingPiece = vectored_board[startingPiece_idx]

        for i in range(startingPiece_numRotation):
            startingPiece = surgeon.rotate_piece_inBits(startingPiece)
        solvingBoard[0,0] = startingPiece

        #Marks the chosen piece as unavailable in the boolean mask
        available_mask[startingPiece_idx] = False

        #Add this starting case to end of queue
        queue.append(
            (solvingBoard, available_mask)
        )
    #Calculate how many diagonal layers to go through 
    numberOfLayers = (2*n) - 2
    for layer in range(numberOfLayers):
        #Record how many parents are present
        numberOfParents = len(queue)
        for parent in range(numberOfParents):
            #grab parent from queue
            solvingBoard, available_mask = queue.popleft()
            #breed children from it
            children = BFS.compute_layer(
                solvingBoard,
                available_mask,
                vectored_board
            )
            #make the children stand to be ready to breed at next layer
            queue.extend(children)

            #Report stuff, non-crucial
            current_time = time.perf_counter()

            if current_time >= next_report_time:
                elapsed_time = (
                    current_time - puzzle_start_time
                )

                print(
                    f"[{elapsed_time:.2f} seconds] "
                    f"Puzzle {i + 1}: "
                    f"filling layer {layer + 1} "
                    f"of {numberOfLayers}; "
                    f"parent {parent + 1} "
                    f"of {numberOfParents}; "
                    f"current queue size: {len(queue)}",
                    flush=True
                )

                # Move the next report time forward while
                # preserving the selected interval.
                while next_report_time <= current_time:
                    next_report_time += (
                        REPORT_INTERVAL
                    )
                #---------------
    #Now that the last layer is done, all the children standing after the very last layer are the solutions (they've been self-bred(?) for n*2-2 generations)
    '''
    Simple printing
    print("Puzzle finished")
    print("Found solutions:")
    print(queue)
    '''
    puzzle_end_time = time.perf_counter()
    solving_time = (
        puzzle_end_time - puzzle_start_time
    )

    numberOfSolutions = len(queue)

    print("\n" + "-" * 70)
    print(f"Puzzle {i + 1} finished")
    print(f"Time used: {solving_time:.6f} seconds")
    print(f"Solutions found: {numberOfSolutions}")
    print("-" * 70)

    # Print every solution in both packed and decoded form.
    for solution_number, solution_case in enumerate(
        queue,
        start=1
    ):
        packed_solution, final_available_mask = (
            solution_case
        )

        decoded_solution = decode_solution(
            packed_solution
        )

        print("\n" + "=" * 70)
        print(
            f"Puzzle {i + 1}, "
            f"solution {solution_number} "
            f"of {numberOfSolutions}"
        )
        print("=" * 70)

        print("\nPacked uint16 solution:")
        print(packed_solution)

        print(
            "\nDecoded solution "
            "[Top, Right, Bottom, Left]:"
        )
        print(decoded_solution)

    print("\n" + "=" * 70)
    print(
        f"End of report for puzzle "
        f"{i + 1}"
    )
    print("=" * 70)