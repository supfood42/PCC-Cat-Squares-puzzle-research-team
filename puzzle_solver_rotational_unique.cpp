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
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

using namespace std;

using Piece = array<int, 4>;

struct Cell
{
    int id = -1;
    int rot = 0;
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

struct SearchResult
{
    int distinct_solution_count;
    unsigned long long raw_solution_count;
    unsigned long long nodes;
    int thread_count;
    vector<vector<Cell>> solution;
};

struct FileInfo
{
    int size;
    int puzzle_count;
};

int n = 0;

vector<Piece> pieces;
vector<array<Piece, 4>> rotations;

vector<Candidate> all_candidates;
unordered_map<int, vector<Candidate>> by_top;
unordered_map<int, vector<Candidate>> by_left;
unordered_map<uint64_t, vector<Candidate>> by_top_left;

Piece rotate90(const Piece& piece)
{
    return {piece[3], piece[0], piece[1], piece[2]};
}

uint64_t edge_pair_key(int top, int left)
{
    return (static_cast<uint64_t>(static_cast<uint32_t>(top)) << 32) |
           static_cast<uint32_t>(left);
}

void build_rotations()
{
    rotations.resize(pieces.size());

    for (size_t id = 0; id < pieces.size(); id++)
    {
        rotations[id][0] = pieces[id];

        for (int rot = 1; rot < 4; rot++)
            rotations[id][rot] = rotate90(rotations[id][rot - 1]);
    }
}

void build_lookup()
{
    all_candidates.clear();
    by_top.clear();
    by_left.clear();
    by_top_left.clear();

    for (int id = 0; id < static_cast<int>(pieces.size()); id++)
    {
        for (int rot = 0; rot < 4; rot++)
        {
            const Candidate candidate{id, rot};
            const Piece& piece = rotations[id][rot];

            all_candidates.push_back(candidate);
            by_top[piece[0]].push_back(candidate);
            by_left[piece[3]].push_back(candidate);
            by_top_left[edge_pair_key(piece[0], piece[3])].push_back(candidate);
        }
    }
}

const vector<Candidate>& matching_candidates(
    const SearchState& state,
    int row,
    int col)
{
    static const vector<Candidate> empty;

    if (row == 0 && col == 0)
        return all_candidates;

    if (row == 0)
    {
        const Cell& left_cell = state.board[row][col - 1];
        const int required_left =
            -rotations[left_cell.id][left_cell.rot][1];

        const auto it = by_left.find(required_left);
        return it == by_left.end() ? empty : it->second;
    }

    if (col == 0)
    {
        const Cell& top_cell = state.board[row - 1][col];
        const int required_top =
            -rotations[top_cell.id][top_cell.rot][2];

        const auto it = by_top.find(required_top);
        return it == by_top.end() ? empty : it->second;
    }

    const Cell& top_cell = state.board[row - 1][col];
    const Cell& left_cell = state.board[row][col - 1];

    const int required_top =
        -rotations[top_cell.id][top_cell.rot][2];
    const int required_left =
        -rotations[left_cell.id][left_cell.rot][1];

    const auto it =
        by_top_left.find(edge_pair_key(required_top, required_left));

    return it == by_top_left.end() ? empty : it->second;
}

vector<int> canonical_solution(const vector<vector<Cell>>& board)
{
    vector<int> best;

    for (int turn = 0; turn < 4; turn++)
    {
        vector<int> key;
        key.reserve(n * n * 5);

        for (int row = 0; row < n; row++)
        {
            for (int col = 0; col < n; col++)
            {
                int source_row;
                int source_col;

                if (turn == 0)
                {
                    source_row = row;
                    source_col = col;
                }
                else if (turn == 1)
                {
                    source_row = n - 1 - col;
                    source_col = row;
                }
                else if (turn == 2)
                {
                    source_row = n - 1 - row;
                    source_col = n - 1 - col;
                }
                else
                {
                    source_row = col;
                    source_col = n - 1 - row;
                }

                const Cell& cell = board[source_row][source_col];
                const Piece& piece =
                    rotations[cell.id][(cell.rot + turn) % 4];

                key.push_back(cell.id);
                key.insert(key.end(), piece.begin(), piece.end());
            }
        }

        if (turn == 0 || key < best)
            best = move(key);
    }

    return best;
}

bool record_solution(
    const SearchState& state,
    atomic<bool>& stop_search,
    unsigned long long& raw_solution_count,
    int& distinct_solution_count,
    vector<int>& first_canonical,
    vector<vector<Cell>>& saved_solution,
    mutex& solutions_mutex)
{
    lock_guard<mutex> lock(solutions_mutex);

    if (stop_search.load(memory_order_acquire))
        return true;

    raw_solution_count++;

    vector<int> canonical = canonical_solution(state.board);

    if (distinct_solution_count == 0)
    {
        first_canonical = move(canonical);
        saved_solution = state.board;
        distinct_solution_count = 1;
        return false;
    }

    if (canonical != first_canonical)
    {
        distinct_solution_count = 2;
        stop_search.store(true, memory_order_release);
        return true;
    }

    return false;
}

bool dfs(
    SearchState& state,
    int pos,
    atomic<bool>& stop_search,
    unsigned long long& raw_solution_count,
    int& distinct_solution_count,
    vector<int>& first_canonical,
    vector<vector<Cell>>& saved_solution,
    mutex& solutions_mutex)
{
    if (stop_search.load(memory_order_acquire))
        return true;

    state.nodes++;

    if (pos == n * n)
    {
        return record_solution(
            state,
            stop_search,
            raw_solution_count,
            distinct_solution_count,
            first_canonical,
            saved_solution,
            solutions_mutex);
    }

    const int row = pos / n;
    const int col = pos % n;

    for (const Candidate& candidate :
         matching_candidates(state, row, col))
    {
        if (stop_search.load(memory_order_acquire))
            return true;

        if (state.used[candidate.id])
            continue;

        state.board[row][col] = {candidate.id, candidate.rot};
        state.used[candidate.id] = true;

        if (dfs(
                state,
                pos + 1,
                stop_search,
                raw_solution_count,
                distinct_solution_count,
                first_canonical,
                saved_solution,
                solutions_mutex))
        {
            state.used[candidate.id] = false;
            return true;
        }

        state.used[candidate.id] = false;
    }

    return false;
}

SearchResult solve_parallel(int requested_threads)
{
    atomic<int> next_branch{0};
    atomic<bool> stop_search{false};

    unsigned long long raw_solution_count = 0;
    int distinct_solution_count = 0;
    vector<int> first_canonical;
    vector<vector<Cell>> saved_solution;
    mutex solutions_mutex;

    const int branch_count = static_cast<int>(all_candidates.size());
    const int thread_count =
        max(1, min(requested_threads, branch_count));

    vector<unsigned long long> worker_nodes(thread_count);
    vector<thread> workers;
    workers.reserve(thread_count);

    for (int worker_index = 0;
         worker_index < thread_count;
         worker_index++)
    {
        workers.emplace_back([&, worker_index]()
        {
            SearchState state{
                vector<vector<Cell>>(n, vector<Cell>(n)),
                vector<bool>(n * n, false),
                0};

            while (!stop_search.load(memory_order_acquire))
            {
                const int branch_index =
                    next_branch.fetch_add(1, memory_order_relaxed);

                if (branch_index >= branch_count)
                    break;

                fill(state.used.begin(), state.used.end(), false);

                const Candidate first = all_candidates[branch_index];
                state.board[0][0] = {first.id, first.rot};
                state.used[first.id] = true;

                dfs(
                    state,
                    1,
                    stop_search,
                    raw_solution_count,
                    distinct_solution_count,
                    first_canonical,
                    saved_solution,
                    solutions_mutex);
            }

            worker_nodes[worker_index] = state.nodes;
        });
    }

    for (thread& worker : workers)
        worker.join();

    unsigned long long total_nodes = 1;

    for (const unsigned long long count : worker_nodes)
        total_nodes += count;

    return {
        distinct_solution_count,
        raw_solution_count,
        total_nodes,
        thread_count,
        move(saved_solution)};
}

string filename_only(const string& path)
{
    const size_t slash = path.find_last_of("/\\");
    return slash == string::npos ? path : path.substr(slash + 1);
}

bool parse_filename(const string& path, FileInfo& info)
{
    const regex pattern(
        R"(^scrambledPuzzles_(\d+)x(\d+)_(\d+)\.txt$)");

    smatch match;
    const string filename = filename_only(path);

    if (!regex_match(filename, match, pattern))
        return false;

    try
    {
        const int rows = stoi(match[1].str());
        const int cols = stoi(match[2].str());
        const int count = stoi(match[3].str());

        if (rows <= 0 || rows != cols || count <= 0)
            return false;

        info = {rows, count};
        return true;
    }
    catch (...)
    {
        return false;
    }
}

bool load_puzzles(
    const string& path,
    int puzzle_count,
    vector<vector<Piece>>& puzzles)
{
    ifstream input(path);

    if (!input)
        return false;

    puzzles.assign(
        puzzle_count,
        vector<Piece>(n * n));

    for (auto& puzzle : puzzles)
    {
        for (Piece& piece : puzzle)
        {
            for (int& edge : piece)
            {
                if (!(input >> edge))
                    return false;
            }
        }
    }

    int extra;
    return !(input >> extra);
}

void initialize_puzzle(const vector<Piece>& puzzle)
{
    pieces = puzzle;
    build_rotations();
    build_lookup();
}

void print_solution(const vector<vector<Cell>>& solution)
{
    for (const auto& row : solution)
    {
        for (const Cell& cell : row)
            cout << cell.id << '(' << cell.rot << ") ";

        cout << '\n';
    }
}

void print_puzzle(const vector<Piece>& puzzle)
{
    for (const Piece& piece : puzzle)
    {
        cout << piece[0] << ' '
             << piece[1] << ' '
             << piece[2] << ' '
             << piece[3] << '\n';
    }
}

bool parse_thread_count(
    int argc,
    char* argv[],
    int& thread_count)
{
    if (argc < 3)
    {
        const unsigned int detected = thread::hardware_concurrency();
        thread_count = detected == 0 ? 1 : static_cast<int>(detected);
        return true;
    }

    try
    {
        thread_count = stoi(argv[2]);
        return thread_count > 0;
    }
    catch (...)
    {
        return false;
    }
}

int main(int argc, char* argv[])
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

    int requested_threads;
    FileInfo file_info;
    vector<vector<Piece>> puzzles;

    if (!parse_thread_count(argc, argv, requested_threads) ||
        !parse_filename(file_path, file_info))
    {
        return 1;
    }

    n = file_info.size;

    if (!load_puzzles(file_path, file_info.puzzle_count, puzzles))
        return 1;

    cout << "Loaded " << file_info.puzzle_count
         << " puzzles of size " << n << 'x' << n << ".\n";
    cout << "Requested CPU threads: " << requested_threads << "\n";

    const auto total_start = chrono::steady_clock::now();

    for (int puzzle_index = 0;
         puzzle_index < file_info.puzzle_count;
         puzzle_index++)
    {
        initialize_puzzle(puzzles[puzzle_index]);

        cout << "\nPuzzle " << puzzle_index + 1
             << " of " << file_info.puzzle_count << '\n';

        const auto start = chrono::steady_clock::now();
        SearchResult result = solve_parallel(requested_threads);
        const double elapsed_ms =
            chrono::duration<double, milli>(
                chrono::steady_clock::now() - start).count();

        cout << fixed << setprecision(3);
        cout << "Threads used: " << result.thread_count << '\n';

        if (result.distinct_solution_count > 1)
        {
            cout << "Multiple solutions up to board rotation.\n";
        }
        else if (result.distinct_solution_count == 1)
        {
            const double total_ms =
                chrono::duration<double, milli>(
                    chrono::steady_clock::now() - total_start).count();

            cout << "Found exactly 1 solution up to board rotation in puzzle "
                 << puzzle_index + 1 << ".\n";
            cout << "Raw rotated solutions found: "
                 << result.raw_solution_count << "\n\n";

            cout << "Original puzzle pieces:\n";
            print_puzzle(puzzles[puzzle_index]);

            cout << "\nRepresentative solution:\n";
            print_solution(result.solution);

            cout << "\nPuzzle time: " << elapsed_ms << " ms\n";
            cout << "Total time: " << total_ms << " ms\n";
            cout << "Tries: " << result.nodes << '\n';
            return 0;
        }
        else
        {
            cout << "No solutions.\n";
        }

        cout << "Raw solutions found: "
             << result.raw_solution_count << '\n';
        cout << "Time: " << elapsed_ms << " ms\n";
        cout << "Tries: " << result.nodes << '\n';
    }

    const double total_ms =
        chrono::duration<double, milli>(
            chrono::steady_clock::now() - total_start).count();

    cout << "\nNo puzzle with exactly 1 solution up to board rotation was found.\n";
    cout << "Checked: " << file_info.puzzle_count << '\n';
    cout << "Total time: " << total_ms << " ms\n";

    return 0;
}
