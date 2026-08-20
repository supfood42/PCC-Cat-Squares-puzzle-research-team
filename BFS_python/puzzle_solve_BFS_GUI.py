import os
import re
import time
import traceback
import multiprocessing as mp
from collections import deque

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import catPuzzleHandling as surgeon
import BFS_functions as BFS

try:
    import psutil
except ImportError:
    psutil = None


# ============================================================
# COLORS
# ============================================================

BG = "#101318"
PANEL = "#181D24"
PANEL2 = "#202630"
TEXT = "#E8EDF3"
SUBTEXT = "#8E9AA8"
BLUE = "#4DA3FF"
GREEN = "#45D483"
RED = "#E53935"
RED_HOVER = "#FF4B47"
YELLOW = "#F2C94C"


# ============================================================
# DATASET PARSING
# ============================================================

def get_dataset_info(filename):

    name = os.path.basename(filename)

    # Examples:
    #
    # scrambledPuzzles_3x3_100000.txt
    # scrambledPuzzles_6x6_100000.txt

    match = re.search(
        r"(\d+)x(\d+).*?(\d+)",
        name,
        re.IGNORECASE
    )

    if not match:
        raise ValueError(
            f"Could not determine puzzle size from:\n{name}\n\n"
            "Expected something like:\n"
            "scrambledPuzzles_6x6_100000.txt"
        )

    rows = int(match.group(1))
    cols = int(match.group(2))
    count = int(match.group(3))

    if rows != cols:
        raise ValueError(
            f"{rows}x{cols} is not a square puzzle."
        )

    return rows, count


# ============================================================
# DATASET LOADING
# ============================================================

def load_dataset(filename):

    n, expected_count = get_dataset_info(filename)

    data = np.loadtxt(
        filename,
        # Remove the delimiter argument entirely so it defaults to whitespace
        dtype=np.int16 # Change to a signed integer to support -1
    )
    
    data = np.asarray(data)

    flat = data.reshape(-1)

    values_per_puzzle = n * n * 4

    if flat.size % values_per_puzzle != 0:

        raise ValueError(
            f"{os.path.basename(filename)} contains "
            f"{flat.size:,} values, which is not divisible by "
            f"{values_per_puzzle:,}."
        )

    actual_count = (
        flat.size // values_per_puzzle
    )

    puzzle_data = flat.reshape(
        actual_count,
        n * n*4
    )

    return puzzle_data, n, actual_count


# ============================================================
# RAM
# ============================================================

def get_ram_mb():

    if psutil is None:
        return 0.0

    try:

        process = psutil.Process()

        return (
            process.memory_info().rss
            / (1024 * 1024)
        )

    except Exception:

        return 0.0


# ============================================================
# SHARED STATISTICS
# ============================================================

def set_stats(stats, lock, **values):

    with lock:

        for key, value in values.items():
            stats[key] = value


# ============================================================
# EXACT ALL-SOLUTIONS BFS
# ============================================================

def solve_dataset(
    filename,
    dataset_index,
    stats,
    lock
):

    dataset_start = time.perf_counter()

    puzzleData, n, numPuzzles = load_dataset(
        filename
    )

    numberOfLayers = (
        2 * n
    ) - 2

    total_solutions = 0

    total_parents = 0
    total_children = 0
    total_complexity = 0

    peak_ram = get_ram_mb()

    set_stats(
        stats,
        lock,

        dataset_index=dataset_index,
        dataset_name=os.path.basename(filename),
        dataset_path=filename,

        n=n,
        num_puzzles=numPuzzles,

        puzzle=0,
        layer=0,
        num_layers=numberOfLayers,

        queue=0,

        parents=0,
        children=0,

        total_parents=0,
        total_children=0,

        current_solutions=0,
        total_solutions=0,

        puzzle_time=0.0,
        dataset_time=0.0,

        lookup_time=0.0,
        bfs_time=0.0,
        layer_time=0.0,

        complexity=0,
        average_complexity=0.0,

        ram=peak_ram,
        peak_ram=peak_ram,

        dataset_finished=False
    )

    # ========================================================
    # PUZZLE LOOP
    # ========================================================

    for puzzle_index in range(numPuzzles):

        puzzle_start = time.perf_counter()

        initialBoard = puzzleData[
            puzzle_index
        ]

        # ----------------------------------------------------
        # BIT REPRESENTATION
        # ----------------------------------------------------

        vectored_board = (
            surgeon.board_to_bits_vector(
                initialBoard
            )
        )

        # ----------------------------------------------------
        # LOOKUP
        # ----------------------------------------------------

        lookup_start = time.perf_counter()

        lookup = BFS.build_lookup(
            vectored_board
        )

        lookup_time = (
            time.perf_counter()
            -
            lookup_start
        )

        # ----------------------------------------------------
        # QUEUE
        # ----------------------------------------------------

        queue = deque()

        # ====================================================
        # EXACT ORIGINAL STARTING STATES
        # ====================================================

        for startCase in range(
            n * n * 4
        ):

            available_mask = np.ones(
                n * n,
                dtype=bool
            )

            solvingBoard = np.zeros(
                (n, n),
                dtype=np.uint16
            )

            startingPiece_idx = (
                startCase // 4
            )

            startingPiece_numRotation = (
                startCase % 4
            )

            startingPiece = (
                vectored_board[
                    startingPiece_idx
                ]
            )

            for rotation in range(
                startingPiece_numRotation
            ):

                startingPiece = (
                    surgeon.rotate_piece_inBits(
                        startingPiece
                    )
                )

            solvingBoard[0, 0] = (
                startingPiece
            )

            available_mask[
                startingPiece_idx
            ] = False

            queue.append(
                (
                    solvingBoard,
                    available_mask
                )
            )

        # ====================================================
        # ALL-SOLUTIONS BFS
        # ====================================================

        bfs_start = time.perf_counter()

        puzzle_parents = 0
        puzzle_children = 0
        puzzle_complexity = 0

        for layer in range(
            numberOfLayers
        ):

            layer_start = time.perf_counter()

            numberOfParents = len(
                queue
            )

            layer_children = 0

            # ------------------------------------------------
            # DO NOT BREAK WHEN A SOLUTION IS FOUND.
            #
            # This is intentionally the original
            # all-solutions BFS.
            # ------------------------------------------------

            for parent in range(
                numberOfParents
            ):

                solvingBoard, available_mask = (
                    queue.popleft()
                )

                children = BFS.compute_layer(
                    solvingBoard,
                    available_mask,
                    lookup
                )

                layer_children += len(
                    children
                )

                queue.extend(
                    children
                )

            # ------------------------------------------------
            # Statistics
            # ------------------------------------------------

            layer_time = (
                time.perf_counter()
                -
                layer_start
            )

            puzzle_parents += (
                numberOfParents
            )

            puzzle_children += (
                layer_children
            )

            total_parents += (
                numberOfParents
            )

            total_children += (
                layer_children
            )

            puzzle_complexity += (
                numberOfParents
                +
                layer_children
            )

            total_complexity += (
                numberOfParents
                +
                layer_children
            )

            ram = get_ram_mb()

            if ram > peak_ram:
                peak_ram = ram

            puzzle_time = (
                time.perf_counter()
                -
                puzzle_start
            )

            dataset_time = (
                time.perf_counter()
                -
                dataset_start
            )

            # ------------------------------------------------
            # Update GUI
            # ------------------------------------------------

            set_stats(
                stats,
                lock,

                puzzle=puzzle_index + 1,
                layer=layer + 1,

                queue=len(queue),

                parents=numberOfParents,
                children=layer_children,

                total_parents=total_parents,
                total_children=total_children,

                current_solutions=0,
                total_solutions=total_solutions,

                puzzle_time=puzzle_time,
                dataset_time=dataset_time,

                lookup_time=lookup_time,

                bfs_time=(
                    time.perf_counter()
                    -
                    bfs_start
                ),

                layer_time=layer_time,

                complexity=puzzle_complexity,

                average_complexity=(
                    total_complexity
                    /
                    (puzzle_index + 1)
                ),

                ram=ram,
                peak_ram=peak_ram
            )

        # ====================================================
        # COMPLETE PUZZLE
        # ====================================================

        number_of_solutions = len(
            queue
        )

        total_solutions += (
            number_of_solutions
        )

        puzzle_time = (
            time.perf_counter()
            -
            puzzle_start
        )

        dataset_time = (
            time.perf_counter()
            -
            dataset_start
        )

        ram = get_ram_mb()

        if ram > peak_ram:
            peak_ram = ram

        set_stats(
            stats,
            lock,

            puzzle=puzzle_index + 1,

            layer=numberOfLayers,

            queue=number_of_solutions,

            current_solutions=(
                number_of_solutions
            ),

            total_solutions=(
                total_solutions
            ),

            puzzle_time=puzzle_time,

            dataset_time=dataset_time,

            complexity=puzzle_complexity,

            average_complexity=(
                total_complexity
                /
                (puzzle_index + 1)
            ),

            ram=ram,
            peak_ram=peak_ram
        )

    # ========================================================
    # DATASET COMPLETE
    # ========================================================

    total_time = (
        time.perf_counter()
        -
        dataset_start
    )

    average_time = (
        total_time / numPuzzles
        if numPuzzles
        else 0
    )

    average_solutions = (
        total_solutions / numPuzzles
        if numPuzzles
        else 0
    )

    average_complexity = (
        total_complexity / numPuzzles
        if numPuzzles
        else 0
    )

    result = {
        "filename": filename,
        "name": os.path.basename(filename),
        "n": n,
        "puzzles": numPuzzles,

        "total_time": total_time,
        "average_time": average_time,

        "total_solutions": total_solutions,
        "average_solutions": average_solutions,

        "average_complexity": average_complexity,

        "peak_ram": peak_ram
    }

    set_stats(
        stats,
        lock,

        dataset_finished=True,

        dataset_time=total_time,

        dataset_average_time=average_time,

        dataset_total_solutions=(
            total_solutions
        ),

        dataset_average_solutions=(
            average_solutions
        ),

        dataset_average_complexity=(
            average_complexity
        ),

        dataset_peak_ram=peak_ram
    )

    return result


# ============================================================
# SOLVER PROCESS
# ============================================================

def solver_process(
    filenames,
    stats,
    lock,
    results
):

    try:

        overall_start = time.perf_counter()

        set_stats(
            stats,
            lock,
            running=True,
            finished=False,
            error=""
        )

        for dataset_index, filename in enumerate(
            filenames
        ):

            result = solve_dataset(
                filename,
                dataset_index,
                stats,
                lock
            )

            results.append(
                result
            )

        overall_time = (
            time.perf_counter()
            -
            overall_start
        )

        set_stats(
            stats,
            lock,

            running=False,
            finished=True,

            overall_time=overall_time
        )

    except Exception:

        set_stats(
            stats,
            lock,

            running=False,
            finished=True,

            error=traceback.format_exc()
        )


# ============================================================
# DATASET ROW
# ============================================================

class DatasetRow(tk.Frame):

    def __init__(
        self,
        parent,
        filename,
        n,
        count,
        remove_callback
    ):

        super().__init__(
            parent,
            bg=PANEL2,
            height=70
        )

        self.filename = filename
        self.n = n
        self.count = count
        self.remove_callback = remove_callback

        self.pack_propagate(False)

        # ----------------------------------------------------
        # Status indicator
        # ----------------------------------------------------

        self.status = tk.Label(
            self,
            text="○",
            bg=PANEL2,
            fg=SUBTEXT,
            font=(
                "Segoe UI",
                20
            )
        )

        self.status.pack(
            side="left",
            padx=(15, 10)
        )

        # ----------------------------------------------------
        # Main information
        # ----------------------------------------------------

        info = tk.Frame(
            self,
            bg=PANEL2
        )

        info.pack(
            side="left",
            fill="both",
            expand=True
        )

        tk.Label(
            info,
            text=f"{n}×{n}    {count:,} puzzles",
            bg=PANEL2,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            pady=(10, 0)
        )

        self.filename_label = tk.Label(
            info,
            text=os.path.basename(filename),
            bg=PANEL2,
            fg=SUBTEXT,
            font=(
                "Consolas",
                9
            )
        )

        self.filename_label.pack(
            anchor="w"
        )

        # ----------------------------------------------------
        # Result
        # ----------------------------------------------------

        self.result_label = tk.Label(
            self,
            text="WAITING",
            bg=PANEL2,
            fg=SUBTEXT,
            font=(
                "Consolas",
                9
            )
        )

        self.result_label.pack(
            side="left",
            padx=15
        )

        # ----------------------------------------------------
        # Remove
        # ----------------------------------------------------

        self.remove_button = tk.Button(
            self,
            text="×",
            command=self.remove,
            bg=PANEL2,
            fg=SUBTEXT,
            activebackground=PANEL2,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=(
                "Segoe UI",
                16
            ),
            cursor="hand2"
        )

        self.remove_button.pack(
            side="right",
            padx=15
        )

    def remove(self):
        self.remove_callback(self)


# ============================================================
# MAIN GUI
# ============================================================

class App:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Puzzle BFS Benchmark"
        )

        self.root.geometry(
            "1250x900"
        )

        self.root.minsize(
            1000,
            700
        )

        self.root.configure(
            bg=BG
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        # ----------------------------------------------------
        # Multiprocessing
        # ----------------------------------------------------

        self.manager = mp.Manager()

        self.stats = (
            self.manager.dict()
        )

        self.lock = (
            self.manager.Lock()
        )

        self.results = (
            self.manager.list()
        )

        self.process = None

        # ----------------------------------------------------
        # Datasets
        # ----------------------------------------------------

        self.datasets = []
        self.rows = []

        self.last_result_count = 0
        self.finished_handled = False

        # ----------------------------------------------------
        # GUI interval
        # ----------------------------------------------------

        self.update_interval = 0.5

        self.build_gui()

        self.root.after(
            100,
            self.update
        )

    # ========================================================
    # GUI
    # ========================================================

    def build_gui(self):

        # ====================================================
        # HEADER
        # ====================================================

        header = tk.Frame(
            self.root,
            bg=BG
        )

        header.pack(
            fill="x",
            padx=30,
            pady=(25, 15)
        )

        tk.Label(
            header,
            text="PUZZLE BFS",
            bg=BG,
            fg=TEXT,
            font=(
                "Segoe UI",
                26,
                "bold"
            )
        ).pack(
            side="left"
        )

        tk.Label(
            header,
            text="  ALL-SOLUTIONS BENCHMARK",
            bg=BG,
            fg=BLUE,
            font=(
                "Segoe UI",
                12,
                "bold"
            )
        ).pack(
            side="left",
            pady=(8, 0)
        )

        self.state_label = tk.Label(
            header,
            text="READY",
            bg=BG,
            fg=GREEN,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )

        self.state_label.pack(
            side="right"
        )

        # ====================================================
        # DATASET PANEL
        # ====================================================

        dataset_panel = tk.Frame(
            self.root,
            bg=PANEL
        )

        dataset_panel.pack(
            fill="x",
            padx=30,
            pady=5
        )

        title = tk.Frame(
            dataset_panel,
            bg=PANEL
        )

        title.pack(
            fill="x",
            padx=20,
            pady=(15, 8)
        )

        tk.Label(
            title,
            text="DATASETS TO RUN",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                12,
                "bold"
            )
        ).pack(
            side="left"
        )

        self.dataset_count_label = tk.Label(
            title,
            text="0 datasets",
            bg=PANEL,
            fg=SUBTEXT,
            font=(
                "Segoe UI",
                9
            )
        )

        self.dataset_count_label.pack(
            side="right"
        )

        # ----------------------------------------------------
        # Tray
        # ----------------------------------------------------

        self.tray = tk.Frame(
            dataset_panel,
            bg=PANEL
        )

        self.tray.pack(
            fill="x",
            padx=15,
            pady=5
        )

        # Empty message

        self.empty_label = tk.Label(
            self.tray,
            text=(
                "No datasets added\n\n"
                "Click + ADD DATASET to build your benchmark"
            ),
            bg=PANEL2,
            fg=SUBTEXT,
            font=(
                "Segoe UI",
                10
            ),
            height=4
        )

        self.empty_label.pack(
            fill="x"
        )

        # ----------------------------------------------------
        # Dataset buttons
        # ----------------------------------------------------

        buttons = tk.Frame(
            dataset_panel,
            bg=PANEL
        )

        buttons.pack(
            fill="x",
            padx=20,
            pady=(8, 18)
        )

        self.add_button = tk.Button(
            buttons,
            text="+  ADD DATASET",
            command=self.add_dataset,
            bg=PANEL2,
            fg=TEXT,
            activebackground="#303946",
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            cursor="hand2"
        )

        self.add_button.pack(
            side="left"
        )

        # ====================================================
        # BIG RUN BUTTON
        # ====================================================

        self.run_button = tk.Button(
            self.root,
            text="RUN",
            command=self.run,
            bg=RED,
            fg="white",
            activebackground=RED_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            font=(
                "Segoe UI",
                22,
                "bold"
            ),
            cursor="hand2",
            height=2
        )

        self.run_button.pack(
            fill="x",
            padx=30,
            pady=15
        )

        # ====================================================
        # CURRENTLY RUNNING
        # ====================================================

        running_panel = tk.Frame(
            self.root,
            bg=PANEL
        )

        running_panel.pack(
            fill="x",
            padx=30,
            pady=5
        )

        tk.Label(
            running_panel,
            text="CURRENTLY RUNNING",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 2)
        )

        self.current_label = tk.Label(
            running_panel,
            text="Waiting for benchmark...",
            bg=PANEL,
            fg=SUBTEXT,
            font=(
                "Consolas",
                10
            )
        )

        self.current_label.pack(
            anchor="w",
            padx=20
        )

        self.progress = ttk.Progressbar(
            running_panel,
            mode="determinate"
        )

        self.progress.pack(
            fill="x",
            padx=20,
            pady=12
        )

        # ====================================================
        # STAT BOXES
        # ====================================================

        stats = tk.Frame(
            self.root,
            bg=BG
        )

        stats.pack(
            fill="x",
            padx=30,
            pady=5
        )

        for i in range(6):
            stats.columnconfigure(
                i,
                weight=1
            )

        self.stat_puzzle = self.make_stat(
            stats,
            0,
            "PUZZLE"
        )

        self.stat_layer = self.make_stat(
            stats,
            1,
            "LAYER"
        )

        self.stat_queue = self.make_stat(
            stats,
            2,
            "QUEUE"
        )

        self.stat_ram = self.make_stat(
            stats,
            3,
            "RAM"
        )

        self.stat_time = self.make_stat(
            stats,
            4,
            "TIME / PUZZLE"
        )

        self.stat_rate = self.make_stat(
            stats,
            5,
            "PUZZLES / SEC"
        )

        # ====================================================
        # DIAGNOSTICS
        # ====================================================

        diagnostics = tk.Frame(
            self.root,
            bg=BG
        )

        diagnostics.pack(
            fill="x",
            padx=30,
            pady=5
        )

        for i in range(5):
            diagnostics.columnconfigure(
                i,
                weight=1
            )

        self.diag_parents = self.make_stat(
            diagnostics,
            0,
            "PARENTS / LAYER"
        )

        self.diag_children = self.make_stat(
            diagnostics,
            1,
            "CHILDREN / LAYER"
        )

        self.diag_avg_children = self.make_stat(
            diagnostics,
            2,
            "AVG CHILDREN"
        )

        self.diag_solutions = self.make_stat(
            diagnostics,
            3,
            "SOLUTIONS"
        )

        self.diag_complexity = self.make_stat(
            diagnostics,
            4,
            "COMPLEXITY"
        )

        # ====================================================
        # GRAPH
        # ====================================================

        graph_panel = tk.Frame(
            self.root,
            bg=PANEL
        )

        graph_panel.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(8, 15)
        )

        tk.Label(
            graph_panel,
            text="AVERAGE SOLVE TIME BY PUZZLE SIZE",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=20,
            pady=(12, 0)
        )

        self.figure = Figure(
            figsize=(8, 3),
            dpi=100
        )

        self.ax = self.figure.add_subplot(
            111
        )

        self.setup_graph()

        self.canvas = (
            FigureCanvasTkAgg(
                self.figure,
                master=graph_panel
            )
        )

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5
        )

        # ====================================================
        # FOOTER / UPDATE SLIDER
        # ====================================================

        footer = tk.Frame(
            self.root,
            bg=BG
        )

        footer.pack(
            fill="x",
            padx=30,
            pady=(0, 12)
        )

        tk.Label(
            footer,
            text="GUI update interval",
            bg=BG,
            fg=SUBTEXT
        ).pack(
            side="left"
        )

        self.interval_var = tk.DoubleVar(
            value=0.5
        )

        tk.Scale(
            footer,
            from_=0.1,
            to=5.0,
            resolution=0.1,
            orient="horizontal",
            variable=self.interval_var,
            command=self.change_interval,
            bg=BG,
            fg=TEXT,
            troughcolor=PANEL2,
            highlightthickness=0,
            showvalue=False,
            length=220
        ).pack(
            side="left",
            padx=10
        )

        self.interval_text = tk.Label(
            footer,
            text="0.5 s",
            bg=BG,
            fg=TEXT
        )

        self.interval_text.pack(
            side="left"
        )

    # ========================================================
    # STAT
    # ========================================================

    def make_stat(
        self,
        parent,
        column,
        title
    ):

        frame = tk.Frame(
            parent,
            bg=PANEL
        )

        frame.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=3
        )

        tk.Label(
            frame,
            text=title,
            bg=PANEL,
            fg=SUBTEXT,
            font=(
                "Segoe UI",
                8,
                "bold"
            )
        ).pack(
            pady=(8, 0)
        )

        value = tk.Label(
            frame,
            text="-",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Consolas",
                12,
                "bold"
            )
        )

        value.pack(
            pady=(0, 8)
        )

        return value

    # ========================================================
    # GRAPH
    # ========================================================

    def setup_graph(self):

        self.ax.clear()

        self.ax.set_facecolor(
            PANEL
        )

        self.figure.patch.set_facecolor(
            PANEL
        )

        self.ax.set_title(
            "Average time to find ALL solutions",
            color=TEXT
        )

        self.ax.set_xlabel(
            "Puzzle size",
            color=SUBTEXT
        )

        self.ax.set_ylabel(
            "Seconds / puzzle",
            color=SUBTEXT
        )

        self.ax.tick_params(
            colors=SUBTEXT
        )

        self.canvas_draw()

    def canvas_draw(self):

        try:
            self.canvas.draw_idle()
        except AttributeError:
            pass

    # ========================================================
    # ADD DATASET
    # ========================================================

    def add_dataset(self):

        if (
            self.process is not None
            and
            self.process.is_alive()
        ):
            return

        files = filedialog.askopenfilenames(
            title="Add puzzle datasets",
            filetypes=[
                (
                    "Puzzle datasets",
                    "*.txt"
                ),
                (
                    "All files",
                    "*.*"
                )
            ]
        )

        for filename in files:

            if filename in self.datasets:
                continue

            try:

                n, count = (
                    get_dataset_info(
                        filename
                    )
                )

            except Exception as e:

                messagebox.showerror(
                    "Invalid dataset",
                    str(e)
                )

                continue

            self.datasets.append(
                filename
            )

            row = DatasetRow(
                self.tray,
                filename,
                n,
                count,
                self.remove_dataset
            )

            row.pack(
                fill="x",
                pady=2
            )

            self.rows.append(
                row
            )

        self.update_dataset_count()

        self.empty_label.pack_forget()

    # ========================================================
    # REMOVE
    # ========================================================

    def remove_dataset(self, row):

        if (
            self.process is not None
            and
            self.process.is_alive()
        ):
            return

        if row.filename in self.datasets:

            index = self.datasets.index(
                row.filename
            )

            self.datasets.pop(
                index
            )

            self.rows.remove(
                row
            )

            row.destroy()

        self.update_dataset_count()

        if not self.datasets:

            self.empty_label.pack(
                fill="x"
            )

    # ========================================================
    # COUNT
    # ========================================================

    def update_dataset_count(self):

        count = len(
            self.datasets
        )

        self.dataset_count_label.config(
            text=(
                f"{count} dataset"
                if count == 1
                else f"{count} datasets"
            )
        )

    # ========================================================
    # RUN
    # ========================================================

    def run(self):

        if not self.datasets:

            messagebox.showwarning(
                "No datasets",
                "Add at least one dataset first."
            )

            return

        if (
            self.process is not None
            and
            self.process.is_alive()
        ):
            return

        # ----------------------------------------------------
        # Reset
        # ----------------------------------------------------

        self.results[:] = []

        self.last_result_count = 0
        self.finished_handled = False

        self.stats.clear()

        # ----------------------------------------------------
        # Initial statistics
        # ----------------------------------------------------

        self.stats.update({
            "running": True,
            "finished": False,
            "error": "",

            "dataset_index": 0,
            "dataset_name": "",

            "n": 0,
            "num_puzzles": 0,

            "puzzle": 0,
            "layer": 0,
            "num_layers": 0,

            "queue": 0,

            "parents": 0,
            "children": 0,

            "total_parents": 0,
            "total_children": 0,

            "current_solutions": 0,
            "total_solutions": 0,

            "puzzle_time": 0,
            "dataset_time": 0,

            "complexity": 0,
            "average_complexity": 0,

            "ram": 0,
            "peak_ram": 0,

            "dataset_finished": False
        })

        # ----------------------------------------------------
        # Lock controls
        # ----------------------------------------------------

        self.add_button.config(
            state="disabled"
        )

        for row in self.rows:

            row.remove_button.config(
                state="disabled"
            )

        self.run_button.config(
            text="RUNNING...",
            bg="#6B1A19",
            state="disabled"
        )

        self.state_label.config(
            text="RUNNING",
            fg=RED
        )

        # ----------------------------------------------------
        # Reset graph
        # ----------------------------------------------------

        self.setup_graph()

        # ----------------------------------------------------
        # Start solver process
        # ----------------------------------------------------

        self.process = mp.Process(
            target=solver_process,
            args=(
                list(self.datasets),
                self.stats,
                self.lock,
                self.results
            )
        )

        self.process.start()

    # ========================================================
    # UPDATE INTERVAL
    # ========================================================

    def change_interval(
        self,
        value
    ):

        self.update_interval = float(
            value
        )

        self.interval_text.config(
            text=f"{self.update_interval:.1f} s"
        )

    # ========================================================
    # MAIN GUI UPDATE
    # ========================================================

    def update(self):

        try:

            with self.lock:

                stats = dict(
                    self.stats
                )

            self.update_stats(
                stats
            )

            self.update_rows()

            self.update_graph()

            if (
                stats.get(
                    "finished",
                    False
                )
                and
                not self.finished_handled
            ):

                self.finished_handled = True

                self.finished()

        except Exception:

            pass

        delay = max(
            20,
            int(
                self.update_interval
                *
                1000
            )
        )

        self.root.after(
            delay,
            self.update
        )

    # ========================================================
    # STATISTICS
    # ========================================================

    def update_stats(
        self,
        s
    ):

        n = s.get(
            "n",
            0
        )

        puzzle = s.get(
            "puzzle",
            0
        )

        puzzles = s.get(
            "num_puzzles",
            0
        )

        layer = s.get(
            "layer",
            0
        )

        layers = s.get(
            "num_layers",
            0
        )

        queue = s.get(
            "queue",
            0
        )

        dataset_time = s.get(
            "dataset_time",
            0
        )

        # ----------------------------------------------------
        # Current dataset
        # ----------------------------------------------------

        if s.get(
            "dataset_name",
            ""
        ):

            self.current_label.config(
                text=(
                    f"{n}×{n}  •  "
                    f"{s['dataset_name']}  •  "
                    f"Puzzle {puzzle:,} / "
                    f"{puzzles:,}  •  "
                    f"Layer {layer} / {layers}"
                )
            )

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if puzzles:

            self.progress["value"] = (
                puzzle
                /
                puzzles
                *
                100
            )

        else:

            self.progress["value"] = 0

        # ----------------------------------------------------
        # Puzzle
        # ----------------------------------------------------

        self.stat_puzzle.config(
            text=(
                f"{puzzle:,} / {puzzles:,}"
            )
        )

        # ----------------------------------------------------
        # Layer
        # ----------------------------------------------------

        self.stat_layer.config(
            text=(
                f"{layer} / {layers}"
            )
        )

        # ----------------------------------------------------
        # Queue
        # ----------------------------------------------------

        self.stat_queue.config(
            text=f"{queue:,}"
        )

        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        if psutil is None:

            self.stat_ram.config(
                text="N/A"
            )

        else:

            self.stat_ram.config(
                text=(
                    f"{s.get('ram', 0):.1f} MB"
                )
            )

        # ----------------------------------------------------
        # Time / puzzle
        # ----------------------------------------------------

        if puzzle:

            average_time = (
                dataset_time
                /
                puzzle
            )

        else:

            average_time = 0

        self.stat_time.config(
            text=(
                f"{average_time:.6f}s"
            )
        )

        # ----------------------------------------------------
        # Puzzles/sec
        # ----------------------------------------------------

        if dataset_time > 0:

            rate = (
                puzzle
                /
                dataset_time
            )

        else:

            rate = 0

        self.stat_rate.config(
            text=f"{rate:.3f}"
        )

        # ----------------------------------------------------
        # Parents
        # ----------------------------------------------------

        self.diag_parents.config(
            text=(
                f"{s.get('parents', 0):,}"
            )
        )

        # ----------------------------------------------------
        # Children
        # ----------------------------------------------------

        self.diag_children.config(
            text=(
                f"{s.get('children', 0):,}"
            )
        )

        # ----------------------------------------------------
        # Average children
        # ----------------------------------------------------

        parents = s.get(
            "parents",
            0
        )

        children = s.get(
            "children",
            0
        )

        if parents:

            avg_children = (
                children
                /
                parents
            )

        else:

            avg_children = 0

        self.diag_avg_children.config(
            text=f"{avg_children:.3f}"
        )

        # ----------------------------------------------------
        # Solutions
        # ----------------------------------------------------

        self.diag_solutions.config(
            text=(
                f"{s.get('total_solutions', 0):,}"
            )
        )

        # ----------------------------------------------------
        # Complexity
        # ----------------------------------------------------

        self.diag_complexity.config(
            text=(
                f"{s.get('complexity', 0):,}"
            )
        )

    # ========================================================
    # UPDATE DATASET ROWS
    # ========================================================

    def update_rows(self):

        if not self.stats:
            return

        current_index = self.stats.get(
            "dataset_index",
            0
        )

        current_finished = self.stats.get(
            "dataset_finished",
            False
        )

        for i, row in enumerate(
            self.rows
        ):

            if i < current_index:

                row.status.config(
                    text="✓",
                    fg=GREEN
                )

                result = None

                for r in list(
                    self.results
                ):

                    if r["filename"] == row.filename:

                        result = r
                        break

                if result:

                    row.result_label.config(
                        text=(
                            f"{result['average_time']:.6f} s/puzzle"
                        ),
                        fg=GREEN
                    )

            elif i == current_index:

                if current_finished:

                    row.status.config(
                        text="✓",
                        fg=GREEN
                    )

                else:

                    row.status.config(
                        text="▶",
                        fg=RED
                    )

                    row.result_label.config(
                        text="RUNNING",
                        fg=RED
                    )

            else:

                row.status.config(
                    text="○",
                    fg=SUBTEXT
                )

                row.result_label.config(
                    text="WAITING",
                    fg=SUBTEXT
                )

    # ========================================================
    # GRAPH
    # ========================================================

    def update_graph(self):

        results = list(
            self.results
        )

        if not results:
            return

        sizes = [
            r["n"]
            for r in results
        ]

        times = [
            r["average_time"]
            for r in results
        ]

        self.ax.clear()

        self.ax.set_facecolor(
            PANEL
        )

        bars = self.ax.bar(
            [
                f"{n}×{n}"
                for n in sizes
            ],
            times
        )

        self.ax.set_title(
            "Average time to find ALL solutions",
            color=TEXT
        )

        self.ax.set_xlabel(
            "Puzzle size",
            color=SUBTEXT
        )

        self.ax.set_ylabel(
            "Seconds / puzzle",
            color=SUBTEXT
        )

        self.ax.tick_params(
            colors=SUBTEXT
        )

        self.ax.grid(
            axis="y",
            alpha=0.15
        )

        # Value above each bar

        for bar, value in zip(
            bars,
            times
        ):

            self.ax.text(
                bar.get_x()
                +
                bar.get_width() / 2,

                bar.get_height(),

                f"{value:.6f}s",

                ha="center",
                va="bottom",

                color=TEXT,

                fontsize=8
            )

        self.figure.tight_layout()

        self.canvas.draw_idle()

    # ========================================================
    # FINISHED
    # ========================================================

    def finished(self):

        self.state_label.config(
            text="COMPLETE",
            fg=GREEN
        )

        self.run_button.config(
            text="RUN",
            bg=RED,
            state="normal"
        )

        self.add_button.config(
            state="normal"
        )

        for row in self.rows:

            row.remove_button.config(
                state="normal"
            )

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        error = self.stats.get(
            "error",
            ""
        )

        if error:

            messagebox.showerror(
                "Solver error",
                error
            )

            return

        # ----------------------------------------------------
        # Print summary
        # ----------------------------------------------------

        print()
        print("=" * 70)
        print("BENCHMARK COMPLETE")
        print("=" * 70)

        for result in list(
            self.results
        ):

            print(
                f"{result['n']}x{result['n']}"
            )

            print(
                f"  Puzzles: "
                f"{result['puzzles']:,}"
            )

            print(
                f"  Total time: "
                f"{result['total_time']:.6f} s"
            )

            print(
                f"  Time/puzzle: "
                f"{result['average_time']:.6f} s"
            )

            print(
                f"  Total solutions: "
                f"{result['total_solutions']:,}"
            )

            print(
                f"  Average solutions/puzzle: "
                f"{result['average_solutions']:.6f}"
            )

            print(
                f"  Average complexity: "
                f"{result['average_complexity']:.3f}"
            )

            print(
                f"  Peak RAM: "
                f"{result['peak_ram']:.1f} MB"
            )

            print()

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        if (
            self.process is not None
            and
            self.process.is_alive()
        ):

            self.process.terminate()

            self.process.join(
                timeout=1
            )

        try:

            self.manager.shutdown()

        except Exception:
            pass

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

def main():

    # Required for Windows multiprocessing
    mp.freeze_support()

    root = tk.Tk()

    app = App(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()