from itertools import product

vals = [1, 2, 3, 4, -1, -2, -3, -4]
puzzles = list(product([1, 2, 3, 4], [1, 2, 3, 4], vals, vals))

with open("puzzles.txt", "w", encoding="utf-8") as f:
    for p in puzzles:
        f.write(" ".join(map(str, p)) + "\n")

        