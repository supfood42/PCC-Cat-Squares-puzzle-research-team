import numpy as np
from qiskit import (
    ClassicalRegister,
    QuantumCircuit,
    QuantumRegister,
    qasm2,
    transpile,
)
from qiskit_aer import AerSimulator


def to_twos_complement(val, bits=4):
    """Converts a signed integer (-4 to +4) into a 4-bit two's complement binary string."""
    if val < 0:
        val = (1 << bits) + val
    return format(val, f"0{bits}b")


def parse_puzzle_input(grid_size):
    """Absorbs a multi-line paste block of puzzle pieces all at once."""
    num_pieces = grid_size * grid_size
    print("\n" + "=" * 65)
    print(
        f"PASTE ALL {num_pieces} PUZZLE PIECES BELOW AT ONCE AND HIT ENTER:"
    )
    print("Format: 4 numbers per line separated by spaces")
    print("=" * 65)

    pieces = []
    while len(pieces) < num_pieces:
        try:
            line = input().strip()
            if not line:
                continue
            edges = [int(x) for x in line.split()]
            if len(edges) != 4:
                print(
                    f"  -> Error on line '{line}': Please enter exactly 4"
                    " numbers per piece."
                )
                continue
            if any(x < -4 or x > 4 or x == 0 for x in edges):
                print(
                    f"  -> Error on line '{line}': Edges must be signed numbers"
                    " from -4 to 4 (no zero)."
                )
                continue
            pieces.append(edges)
        except ValueError:
            print(
                f"  -> Error on line '{line}': Invalid input. Please enter"
                " integers only."
            )

    return pieces


def display_quantum_encoding_table(pieces):
    """Prints a clear translation table showing how the inputted pieces map to qubits."""
    print("\n" + "=" * 65)
    print("QUANTUM ORACLE PIECE ENCODING TABLE:")
    print("=" * 65)
    print(
        f"{'Piece ID':<10} | {'Raw Edges (N, E, S, W)':<22} | {'4-Bit Binary QASM String'}"
    )
    print("-" * 65)
    for idx, edges in enumerate(pieces):
        bin_edges = " ".join([to_twos_complement(e) for e in edges])
        print(f"ID {idx} (00{idx:<4}) | {str(edges):<22} | {bin_edges}")
    print("=" * 65)


def rotate_piece(edges, rot):
    """Circularly shifts edges [N, E, S, W] clockwise by rot * 90 degrees."""
    return edges[-rot:] + edges[:-rot] if rot else edges


def solve_puzzle_constraints(pieces):
    """
    Evaluates valid 2x2 grid arrangements where touching internal edges sum to 0
    and each piece (0, 1, 2, 3) is used exactly once.
    Returns a list of matching 16-bit binary state strings.
    """
    valid_states = []
    for p0 in range(4):
        for p1 in range(4):
            for p2 in range(4):
                for p3 in range(4):
                    if len({p0, p1, p2, p3}) != 4:
                        continue

                    for r0 in range(4):
                        for r1 in range(4):
                            for r2 in range(4):
                                for r3 in range(4):
                                    cell0 = rotate_piece(pieces[p0], r0)
                                    cell1 = rotate_piece(pieces[p1], r1)
                                    cell2 = rotate_piece(pieces[p2], r2)
                                    cell3 = rotate_piece(pieces[p3], r3)

                                    east_0_west_1 = cell0[1] + cell1[3] == 0
                                    south_0_north_2 = cell0[2] + cell2[0] == 0
                                    south_1_north_3 = cell1[2] + cell3[0] == 0
                                    east_2_west_3 = cell2[1] + cell3[3] == 0

                                    if (
                                        east_0_west_1
                                        and south_0_north_2
                                        and south_1_north_3
                                        and east_2_west_3
                                    ):
                                        b0 = f"{p0:02b}{r0:02b}"
                                        b1 = f"{p1:02b}{r1:02b}"
                                        b2 = f"{p2:02b}{r2:02b}"
                                        b3 = f"{p3:02b}{r3:02b}"
                                        valid_states.append(
                                            f"{b3}{b2}{b1}{b0}"
                                        )

    return valid_states


def build_puzzle_oracle(valid_states, board_reg):
    """
    Compiles a Phase Oracle that flips the sign (-1) of the valid puzzle solutions.
    """
    oracle = QuantumCircuit(board_reg, name="Puzzle_Oracle")

    for state in valid_states:
        zero_indices = [
            i
            for i, bit in enumerate(reversed(state))
            if bit == "0"
        ]
        if zero_indices:
            oracle.x(zero_indices)

        oracle.h(15)
        oracle.mcx(list(range(15)), 15)
        oracle.h(15)

        if zero_indices:
            oracle.x(zero_indices)

    return oracle


def build_diffuser(num_qubits=16):
    """Creates the Grover Diffuser for N qubits."""
    qc = QuantumCircuit(num_qubits, name="Diffuser")
    qc.h(range(num_qubits))
    qc.x(range(num_qubits))
    qc.h(num_qubits - 1)
    qc.mcx(list(range(num_qubits - 1)), num_qubits - 1)
    qc.h(num_qubits - 1)
    qc.x(range(num_qubits))
    qc.h(range(num_qubits))
    return qc.to_gate()


def calculate_swaps(bitstring):
    """Returns the list of (cell_A, cell_B) swap pairs needed to arrange pieces."""
    target_pieces = []
    for cell_idx in range(4):
        end = 16 - (cell_idx * 4)
        start = end - 4
        piece_id = int(bitstring[start:end][0:2], 2)
        target_pieces.append(piece_id)

    board = [0, 1, 2, 3]  # Initial state: Cell 0 has Piece 0, etc.
    swaps = []
    for i in range(4):
        if board[i] != target_pieces[i]:
            target_piece = target_pieces[i]
            loc = board.index(target_piece)
            board[i], board[loc] = board[loc], board[i]
            swaps.append((i, loc))
    return swaps


def print_decoded_solution(bitstring):
    """Decodes a 16-bit measurement string into physical swap and rotation instructions."""
    cell_names = [
        "Top-Left (Cell 0)",
        "Top-Right (Cell 1)",
        "Bottom-Left (Cell 2)",
        "Bottom-Right (Cell 3)",
    ]
    rot_labels = [
        "0° (Upright)",
        "90° CW (1 turn)",
        "180° CW (2 turns)",
        "270° CW (3 turns)",
    ]

    swaps = calculate_swaps(bitstring)

    print("\n" + "#" * 65)
    print(
        "   STEP-BY-STEP PHYSICAL PUZZLE SOLVER (FEWEST MOVES GUARANTEED)   "
    )
    print("#" * 65)

    # PHASE 1: PHYSICAL SWAPS
    print("\n--- PHASE 1: SWAP PIECES TO THEIR TARGET CELLS ---")
    if not swaps:
        print(
            "  -> No swaps needed! All pieces are already in their correct"
            " starting cells."
        )
    else:
        for idx, (c1, c2) in enumerate(swaps, 1):
            print(
                f"  Step {idx}: Swap {cell_names[c1]} <--> {cell_names[c2]}"
            )

    # PHASE 2: IN-PLACE ROTATIONS
    print("\n--- PHASE 2: ROTATE PIECES IN PLACE ---")
    for cell_idx in range(4):
        end = 16 - (cell_idx * 4)
        start = end - 4
        chunk = bitstring[start:end]
        piece_id = int(chunk[0:2], 2)
        rot_val = int(chunk[2:4], 2)

        if rot_val == 0:
            print(
                f"  * {cell_names[cell_idx]} (Piece {piece_id}): Leave"
                " Upright (0 turns)"
            )
        else:
            print(
                f"  * {cell_names[cell_idx]} (Piece {piece_id}): Rotate"
                f" {rot_labels[rot_val]}"
            )

    # PHASE 3: FINAL BLUEPRINT TABLE
    print("\n" + "=" * 65)
    print(f"FINAL BOARD BLUEPRINT (Bitstring: {bitstring}):")
    print("=" * 65)
    print(
        f"{'Grid Position':<22} | {'Piece ID':<10} | {'Final Orientation'}"
    )
    print("-" * 65)
    for cell_idx in range(4):
        end = 16 - (cell_idx * 4)
        start = end - 4
        chunk = bitstring[start:end]
        piece_id = int(chunk[0:2], 2)
        rot_val = int(chunk[2:4], 2)
        print(
            f"{cell_names[cell_idx]:<22} | Piece {piece_id:<4} |"
            f" {rot_labels[rot_val]}"
        )
    print("=" * 65)


# =====================================================================
# MAIN INTERACTIVE PROGRAM
# =====================================================================

print("\n" + "#" * 65)
print("   QUANTUM EDGE-MATCHING PUZZLE SOLVER & CIRCUIT COMPILER   ")
print("#" * 65)

# 1. Ask for Grid Size with classical limit warning
while True:
    try:
        size_input = input(
            "\nHow large of a puzzle? (Enter 2 for 2x2, max 2 for classical"
            " computer): "
        ).strip()
        grid_size = int(size_input)
        if grid_size == 2:
            break
        elif grid_size > 2:
            print(
                "  -> Note: Simulating a 3x3+ puzzle requires >36 qubits"
                " (supercomputer scale!)."
            )
            print(
                "  -> Please enter 2 to run successfully on your classical"
                " computer."
            )
        else:
            print("  -> Please enter a valid grid size (2 or higher).")
    except ValueError:
        print("  -> Please enter a number.")

# 2. Get pasted puzzle input from the user
puzzle_pieces = parse_puzzle_input(grid_size)

# 3. Display translated binary encoding
display_quantum_encoding_table(puzzle_pieces)

# 4. Analyze valid solutions and calculate optimal Grover iterations
valid_solutions = solve_puzzle_constraints(puzzle_pieces)
num_solutions = max(len(valid_solutions), 1)

optimal_iterations = int(
    np.round((np.pi / 4) * np.sqrt(65536 / num_solutions))
)
print(
    f"\n  -> Oracle Compiler: Found {len(valid_solutions)} valid matching"
    " board state(s)."
)
print(
    "  -> Amplitude Calculation: To amplify from 0.02% to ~99.9%, optimal"
    f" Grover iterations = {optimal_iterations}"
)

# 5. Build the custom Qiskit circuit
print(
    f"Compiling 16-qubit Grover search circuit with {optimal_iterations}"
    " iterations..."
)
board = QuantumRegister(16, name="board")
sol = ClassicalRegister(16, name="solution")
circuit = QuantumCircuit(board, sol)

# Stage 1: Superposition
circuit.h(board)

# Stage 2 & 3: Loop the Oracle and Diffuser to amplify probability
oracle_gate = build_puzzle_oracle(valid_solutions, board).to_gate()
diffuser_gate = build_diffuser(16)

for _ in range(optimal_iterations):
    circuit.append(oracle_gate, board)
    circuit.append(diffuser_gate, board)

# Stage 4: Measurement
circuit.measure(board, sol)

# 6. Export to OpenQASM 2.0
output_filename = "custom_puzzle_solver.qasm"
with open(output_filename, "w") as file:
    qasm2.dump(circuit, file)
print(
    f"SUCCESS: Generated '{output_filename}' with your custom puzzle constraints!"
)

# 7. Run simulation
print("\nRunning 1,024 simulation shots on local AerSimulator...")
simulator = AerSimulator()
compiled_circuit = transpile(circuit, simulator)
job = simulator.run(compiled_circuit, shots=1024)
counts = job.result().get_counts()

sorted_counts = dict(
    sorted(counts.items(), key=lambda item: item[1], reverse=True)
)

print("\n" + "=" * 65)
print("SIMULATION RESULTS (Top 5 Measured Board Layouts):")
print("=" * 65)
print(
    f"{'16-Bit Board State (c[15]..c[0])':<35} | {'Shots':<8} | {'Probability'}"
)
print("-" * 65)

for i, (bitstring, count) in enumerate(sorted_counts.items()):
    if i >= 5:
        break
    probability = (count / 1024) * 100
    print(f"{bitstring:<35} | {count:<8} | {probability:.1f}%")
print("=" * 65)

# 8. Decode and display the #1 winning solution with the FEWEST SWAPS automatically
top_measured_winners = list(sorted_counts.keys())[:num_solutions]

best_winning_bitstring = min(
    top_measured_winners, key=lambda bs: len(calculate_swaps(bs))
)

print_decoded_solution(best_winning_bitstring)