#!/usr/bin/env python3
"""Efficient backtracking solver for n*n tile puzzle.

Input: lines of 4 integers (top right bottom left). Pieces may be rotated.
Matching rule: adjacent sides must sum to zero (color+head/tail).
Output: solved board as oriented pieces (one line per placed piece: 4 ints).
"""

import math
import sys


def rotations(sides):
	t, r, b, l = sides
	return [(t, r, b, l), (l, t, r, b), (b, l, t, r), (r, b, l, t)]


def solve(pieces):
	m = len(pieces)
	n = int(math.isqrt(m))
	if n * n != m:
		return None

	rots = [rotations(tuple(p)) for p in pieces]
	used = [False] * m
	grid = [None] * m
	sys.setrecursionlimit(10000)

	def dfs(pos):
		if pos == m:
			return True
		r = pos // n
		c = pos % n
		need_top = None
		need_left = None
		if r > 0:
			top = grid[pos - n]
			need_top = -top[2]
		if c > 0:
			left = grid[pos - 1]
			need_left = -left[1]

		for i in range(m):
			if used[i]:
				continue
			for rot in rots[i]:
				if need_top is not None and rot[0] != need_top:
					continue
				if need_left is not None and rot[3] != need_left:
					continue
				used[i] = True
				grid[pos] = rot
				if dfs(pos + 1):
					return True
				used[i] = False
		grid[pos] = None
		return False

	return grid if dfs(0) else None


def main():
	pieces = []
	lines = []
	if len(sys.argv) > 1:
		path = sys.argv[1]
		try:
			with open(path, 'r', encoding='utf8') as f:
				lines = f.readlines()
		except Exception as e:
			print(f"Error opening {path}: {e}", file=sys.stderr)
			return
	else:
		# read from stdin
		lines = sys.stdin.readlines()

	for line in lines:
		s = line.strip()
		if not s:
			continue
		parts = s.split()
		if len(parts) < 4:
			continue
		pieces.append([int(x) for x in parts[:4]])

	if not pieces:
		print("No input", file=sys.stderr)
		return

	sol = solve(pieces)
	if sol is None:
		print("No solution", file=sys.stderr)
		return

	for p in sol:
		print(p[0], p[1], p[2], p[3])


if __name__ == '__main__':
	main()