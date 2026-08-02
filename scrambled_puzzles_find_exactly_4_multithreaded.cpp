#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <regex>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

using namespace std;

int n = 0;

struct Edge
{
    int value;
};

struct Piece
{
    Edge e[4];
};

struct Cell
{
    int id;
    int rot;
    Piece p;
};

struct Candidate
{
    int id;
    int rot;
};

struct SearchState
{
    vector<vector<Cell>> board;
    vector<bool> used;
    unsigned long long nodes = 0;
};

vector<Piece> pieces;
vector<array<Piece, 4>> rot;

vector<Candidate> all_candidates;
unordered_map<int, vector<Candidate>> by_top;
unordered_map<int, vector<Candidate>> by_left;
unordered_map<uint64_t, vector<Candidate>> by_top_left;

Piece rotate90(Piece p)
{
    Piece q;
    q.e[0] = p.e[3];
    q.e[1] = p.e[0];
    q.e[2] = p.e[1];
    q.e[3] = p.e[2];
    return q;
}

uint64_t edge_pair_key(int top, int left)
{
    return (static_cast<uint64_t>(static_cast<uint32_t>(top)) << 32) |
           static_cast<uint32_t>(left);
}

void build_rotations()
{
    for (int i = 0; i < n * n; i++)
    {
        rot[i][0] = pieces[i];

        for (int r = 1; r < 4; r++)
            rot[i][r] = rotate90(rot[i][r - 1]);
    }
}

void build_lookup()
{
    all_candidates.clear();
    by_top.clear();
    by_left.clear();
    by_top_left.clear();

    for (int id = 0; id < n * n; id++)
    {
        for (int rotation = 0; rotation < 4; rotation++)
        {
            Candidate candidate{id, rotation};
            int top = rot[id][rotation].e[0].value;
            int left = rot[id][rotation].e[3].value;

            all_candidates.push_back(candidate);
            by_top[top].push_back(candidate);
            by_left[left].push_back(candidate);
            by_top_left[edge_pair_key(top, left)].push_back(candidate);
        }
    }
}

const vector<Candidate>& matching_candidates(
    const SearchState& state,
    int r,
    int c)
{
    static const vector<Candidate> empty;

    if (r == 0 && c == 0)
        return all_candidates;

    if (r == 0)
    {
        int required_left = -state.board[r][c - 1].p.e[1].value;
        auto it = by_left.find(required_left);
        return it == by_left.end() ? empty : it->second;
    }

    if (c == 0)
    {
        int required_top = -state.board[r - 1][c].p.e[2].value;
        auto it = by_top.find(required_top);
        return it == by_top.end() ? empty : it->second;
    }

    int required_top = -state.board[r - 1][c].p.e[2].value;
    int required_left = -state.board[r][c - 1].p.e[1].value;
    auto it = by_top_left.find(edge_pair_key(required_top, required_left));
    return it == by_top_left.end() ? empty : it->second;
}

bool record_solution(
    const SearchState& state,
    atomic<int>& solution_count,
    atomic<bool>& stop_search,
    vector<vector<vector<Cell>>>& saved_solutions,
    mutex& solutions_mutex)
{
    int current = solution_count.load(memory_order_relaxed);

    while (current < 5)
    {
        if (solution_count.compare_exchange_weak(
                current,
                current + 1,
                memory_order_acq_rel,
                memory_order_relaxed))
        {
            const int solution_number = current + 1;

            if (solution_number <= 4)
            {
                lock_guard<mutex> lock(solutions_mutex);
                saved_solutions[solution_number - 1] = state.board;
            }

            if (solution_number == 5)
            {
                stop_search.store(true, memory_order_release);
                return true;
            }

            return false;
        }
    }

    stop_search.store(true, memory_order_release);
    return true;
}

bool dfs(
    SearchState& state,
    int pos,
    atomic<int>& solution_count,
    atomic<bool>& stop_search,
    vector<vector<vector<Cell>>>& saved_solutions,
    mutex& solutions_mutex)
{
    if (stop_search.load(memory_order_acquire))
        return true;

    state.nodes++;

    if (pos == n * n)
    {
        return record_solution(
            state,
            solution_count,
            stop_search,
            saved_solutions,
            solutions_mutex);
    }

    int r = pos / n;
    int c = pos % n;

    const vector<Candidate>& candidates = matching_candidates(state, r, c);

    for (const Candidate& candidate : candidates)
    {
        if (stop_search.load(memory_order_acquire))
            return true;

        if (state.used[candidate.id])
            continue;

        state.board[r][c].id = candidate.id;
        state.board[r][c].rot = candidate.rot;
        state.board[r][c].p = rot[candidate.id][candidate.rot];

        state.used[candidate.id] = true;

        if (dfs(
                state,
                pos + 1,
                solution_count,
                stop_search,
                saved_solutions,
                solutions_mutex))
        {
            state.used[candidate.id] = false;
            return true;
        }

        state.used[candidate.id] = false;
    }

    return false;
}

struct SearchResult
{
    int solution_count = 0;
    unsigned long long nodes = 0;
    int thread_count = 0;
    vector<vector<vector<Cell>>> saved_solutions;
};

SearchResult solve_parallel(int requested_thread_count)
{
    atomic<int> next_branch{0};
    atomic<int> solution_count{0};
    atomic<bool> stop_search{false};

    vector<vector<vector<Cell>>> saved_solutions(4);
    mutex solutions_mutex;

    const int branch_count = static_cast<int>(all_candidates.size());
    const int thread_count = max(1, min(requested_thread_count, branch_count));
    vector<unsigned long long> worker_nodes(thread_count, 0);
    vector<thread> workers;
    workers.reserve(thread_count);

    for (int worker_index = 0; worker_index < thread_count; worker_index++)
    {
        workers.emplace_back([&, worker_index]()
        {
            SearchState state;
            state.board.assign(n, vector<Cell>(n));
            state.used.assign(n * n, false);

            while (!stop_search.load(memory_order_acquire))
            {
                const int branch_index =
                    next_branch.fetch_add(1, memory_order_relaxed);

                if (branch_index >= branch_count)
                    break;

                fill(state.used.begin(), state.used.end(), false);

                const Candidate& first = all_candidates[branch_index];
                state.board[0][0].id = first.id;
                state.board[0][0].rot = first.rot;
                state.board[0][0].p = rot[first.id][first.rot];
                state.used[first.id] = true;

                dfs(
                    state,
                    1,
                    solution_count,
                    stop_search,
                    saved_solutions,
                    solutions_mutex);

                state.used[first.id] = false;
            }

            worker_nodes[worker_index] = state.nodes;
        });
    }

    for (thread& worker : workers)
        worker.join();

    unsigned long long total_nodes = 1;
    for (unsigned long long worker_node_count : worker_nodes)
        total_nodes += worker_node_count;

    return {
        solution_count.load(memory_order_acquire),
        total_nodes,
        thread_count,
        move(saved_solutions)};
}

struct FileInfo
{
    int size;
    int puzzle_count;
};

string filename_only(const string& file_path)
{
    const size_t slash = file_path.find_last_of("/\\");
    return slash == string::npos ? file_path : file_path.substr(slash + 1);
}

FileInfo parse_filename(const string& file_path)
{
    const string filename = filename_only(file_path);
    const regex pattern(R"(^scrambledPuzzles_(\d+)x(\d+)_(\d+)\.txt$)");
    smatch match;

    if (!regex_match(filename, match, pattern))
    {
        throw runtime_error(
            "Filename must use this format: scrambledPuzzles_5x5_10.txt");
    }

    const int rows = stoi(match[1].str());
    const int columns = stoi(match[2].str());
    const int puzzle_count = stoi(match[3].str());

    if (rows <= 0 || rows != columns || puzzle_count <= 0)
        throw runtime_error("The filename must describe one or more square puzzles.");

    return {rows, puzzle_count};
}

vector<vector<Piece>> load_puzzles(
    const string& file_path,
    int puzzle_count)
{
    ifstream input(file_path);

    if (!input)
        throw runtime_error("Could not open file: " + file_path);

    vector<vector<Piece>> puzzles(
        puzzle_count,
        vector<Piece>(n * n));

    for (int puzzle_index = 0; puzzle_index < puzzle_count; puzzle_index++)
    {
        for (int piece_index = 0; piece_index < n * n; piece_index++)
        {
            for (int edge = 0; edge < 4; edge++)
            {
                if (!(input >> puzzles[puzzle_index][piece_index].e[edge].value))
                {
                    throw runtime_error(
                        "The file ended before all " +
                        to_string(puzzle_count) + " puzzles were read.");
                }
            }
        }
    }

    int extra_value;
    if (input >> extra_value)
    {
        throw runtime_error(
            "The file contains more values than expected for " +
            to_string(puzzle_count) + " puzzles of size " +
            to_string(n) + "x" + to_string(n) + ".");
    }

    return puzzles;
}

void initialize_puzzle(const vector<Piece>& puzzle)
{
    pieces = puzzle;
    rot.assign(n * n, {});

    build_rotations();
    build_lookup();
}

void print_solution(const vector<vector<Cell>>& solution)
{
    for (int r = 0; r < n; r++)
    {
        for (int c = 0; c < n; c++)
        {
            cout << solution[r][c].id
                 << "("
                 << solution[r][c].rot
                 << ") ";
        }

        cout << '\n';
    }
}

void print_puzzle(const vector<Piece>& puzzle)
{
    for (const Piece& piece : puzzle)
    {
        cout << piece.e[0].value << ' '
             << piece.e[1].value << ' '
             << piece.e[2].value << ' '
             << piece.e[3].value << '\n';
    }
}

int parse_thread_count(int argc, char* argv[])
{
    if (argc >= 3)
    {
        const int requested = stoi(argv[2]);

        if (requested <= 0)
            throw runtime_error("Thread count must be greater than zero.");

        return requested;
    }

    const unsigned int detected = thread::hardware_concurrency();
    return detected == 0 ? 1 : static_cast<int>(detected);
}

int main(int argc, char* argv[])
{
    try
    {
        string file_path;

        if (argc >= 2)
        {
            file_path = argv[1];
        }
        else
        {
            cout << "Enter puzzle file name: ";
            getline(cin, file_path);
        }

        const int requested_thread_count = parse_thread_count(argc, argv);
        const FileInfo file_info = parse_filename(file_path);
        n = file_info.size;

        const vector<vector<Piece>> puzzles =
            load_puzzles(file_path, file_info.puzzle_count);

        cout << "\nLoaded " << file_info.puzzle_count
             << " puzzles of size " << n << "x" << n << ".\n";
        cout << "Requested CPU threads: " << requested_thread_count << "\n";

        const auto total_start = chrono::steady_clock::now();

        for (int puzzle_index = 0;
             puzzle_index < file_info.puzzle_count;
             puzzle_index++)
        {
            initialize_puzzle(puzzles[puzzle_index]);

            cout << "\n========================================\n";
            cout << "Puzzle " << puzzle_index + 1
                 << " of " << file_info.puzzle_count << '\n';
            cout << "========================================\n";

            const auto puzzle_start = chrono::steady_clock::now();
            SearchResult result = solve_parallel(requested_thread_count);
            const auto puzzle_end = chrono::steady_clock::now();

            const double elapsed_ms =
                chrono::duration<double, milli>(
                    puzzle_end - puzzle_start).count();

            cout << fixed << setprecision(3);
            cout << "Threads used: " << result.thread_count << '\n';

            if (result.solution_count >= 5)
            {
                cout << "More than 4 solutions.\n";
                cout << "Search stopped after finding solution 5.\n";
                cout << "Moving to the next puzzle.\n";
            }
            else if (result.solution_count == 4)
            {
                const auto total_end = chrono::steady_clock::now();
                const double total_ms =
                    chrono::duration<double, milli>(
                        total_end - total_start).count();

                cout << "Found a puzzle with exactly 4 solutions.\n";
                cout << "Puzzle number: " << puzzle_index + 1 << "\n\n";

                cout << "Original puzzle pieces:\n";
                print_puzzle(puzzles[puzzle_index]);

                for (int solution_index = 0;
                     solution_index < 4;
                     solution_index++)
                {
                    cout << "\nSolution " << solution_index + 1 << ":\n";
                    print_solution(result.saved_solutions[solution_index]);
                }

                cout << "\nPuzzle time: " << elapsed_ms << " ms\n";
                cout << "Total time: " << total_ms << " ms\n";
                cout << "Tries: " << result.nodes << '\n';
                cout << "\nStopping program.\n";

                return 0;
            }
            else
            {
                cout << "Solutions found: " << result.solution_count << '\n';
                cout << "Moving to the next puzzle.\n";
            }

            cout << "Time: " << elapsed_ms << " ms\n";
            cout << "Tries: " << result.nodes << '\n';
        }

        const auto total_end = chrono::steady_clock::now();
        const double total_ms =
            chrono::duration<double, milli>(
                total_end - total_start).count();

        cout << "\n========================================\n";
        cout << "No puzzle with exactly 4 solutions was found.\n";
        cout << "Checked: " << file_info.puzzle_count << " puzzles\n";
        cout << "Total time: " << total_ms << " ms\n";

        return 0;
    }
    catch (const exception& error)
    {
        cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
