import time
import tkinter as tk
from tkinter import filedialog
import numpy as np
import re

def rotate_piece(piece):  #rotates piece clockwise
    return [piece[3], piece[0], piece[1], piece[2]]

def pick_random_piece(board):
    while True:
        row = np.random.randint(0, n)
        col = np.random.randint(0, n)

        piece = board[row, col].copy()  # save the piece
        if not np.all(piece == 0):
            board[row, col] = 0  # replace with [0,0,0,0]
            return piece

#reads puzzle dataset line by line, the data is in this form (this is 3x3):
''' 
-1 3 4 -1
1 2 -1 4
1 -4 4 -4
1 2 -1 -3
-3 -2 -1 -2
1 -2 1 4
2 -4 2 -2
-3 2 4 4
-2 3 -1 4
'''
# Select puzzle file
root = tk.Tk()
root.withdraw()

filename = filedialog.askopenfilename()


# Extract n and number of puzzles from filename
n, num_puzzles = map(int, re.search(r'_(\d+)x\d+_(\d+)', filename).groups())

#Initializes a 2D array which is the board with n rows and n columns
initialBoard = np.zeros((n, n, 4), dtype = int)

#writes pieces to initialBoard
with open(filename, "r") as file:
    for row in range(n):
        for col in range(n):
            initialBoard[row, col] = list(map(int, file.readline().split()))


#Initializes a empty 2D array of same size which is 'matchingBoard'
matchingBoard = np.zeros((n, n, 4),dtype = int)

#Debugging: prints dataset
#print(initialBoard)

#picks cneter point
center_row, center_col = n // 2, n // 2
#Fills with random piece
matchingBoard[center_row, center_col] = pick_random_piece(initialBoard)

def find_matching_piece(board, side, value):
    for row, col in np.ndindex(board.shape[:2]):
        if board[row, col, side] == value:
            return row, col

    return None

#Chooses