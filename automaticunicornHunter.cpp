#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <random>
#include <thread>
#include <vector>
#include <string>
#include <sstream>
using namespace std;

using Piece = array<int, 4>;

struct Cell
{
    int id = -1;
    uint8_t rot = 0;
};

struct Candidate
{
    int id;
    uint8_t rot;
};

struct SearchResult
{
    bool valid = false;
    bool aborted = false;
    unsigned long long raw_solutions = 0;
    vector<Cell> solution;
};

constexpr int EDGE_COLORS = 4;
constexpr int EDGE_INDEX_COUNT = 9;
constexpr int MAX_UNIQUE_PIECES = 1044;
constexpr int MAX_GENERATION_RETRIES = 512;
constexpr int TARGET_THREADS_PER_PUZZLE = 8;
constexpr int MAX_CONCURRENT_PUZZLES = 4;

Piece rotate90(const Piece& piece)
{
    return {piece[3], piece[0], piece[1], piece[2]};
}

int edge_index(int edge)
{
    return edge + EDGE_COLORS;
}

uint16_t encode_piece(const Piece& piece)
{
    uint16_t key = 0;

    for (int edge : piece)
    {
        const int value = edge < 0 ? edge + EDGE_COLORS : edge + EDGE_COLORS - 1;
        key = static_cast<uint16_t>((key << 3) | value);
    }

    return key;
}

uint16_t canonical_piece_key(Piece piece)
{
    uint16_t best = encode_piece(piece);

    for (int turn = 1; turn < 4; ++turn)
    {
        piece = rotate90(piece);
        best = min(best, encode_piece(piece));
    }

    return best;
}

int random_edge(mt19937_64& rng)
{
    const uint64_t bits = rng();
    const int value = static_cast<int>(bits & 3ULL) + 1;
    return (bits & 4ULL) ? value : -value;
}

bool generate_solved_puzzle(int n, mt19937_64& rng, vector<Piece>& puzzle)
{
    puzzle.resize(static_cast<size_t>(n) * n);
    array<uint8_t, 4096> used_piece_classes{};

    for (int pos = 0; pos < n * n; ++pos)
    {
        const int row = pos / n;
        const int col = pos % n;
        bool placed = false;

        for (int attempt = 0; attempt < MAX_GENERATION_RETRIES; ++attempt)
        {
            Piece piece;
            piece[0] = row == 0
                ? random_edge(rng)
                : -puzzle[(row - 1) * n + col][2];
            piece[3] = col == 0
                ? random_edge(rng)
                : -puzzle[row * n + col - 1][1];
            piece[1] = random_edge(rng);
            piece[2] = random_edge(rng);

            const uint16_t key = canonical_piece_key(piece);

            if (!used_piece_classes[key])
            {
                used_piece_classes[key] = 1;
                puzzle[pos] = piece;
                placed = true;
                break;
            }
        }

        if (!placed)
            return false;
    }

    return true;
}

vector<Piece> generate_scrambled_puzzle(int n, mt19937_64& rng)
{
    vector<Piece> puzzle;

    while (!generate_solved_puzzle(n, rng, puzzle))
    {
    }

    shuffle(puzzle.begin(), puzzle.end(), rng);
    uniform_int_distribution<int> turn_dist(0, 3);

    for (Piece& piece : puzzle)
    {
        const int turns = turn_dist(rng);
        for (int turn = 0; turn < turns; ++turn)
            piece = rotate90(piece);
    }

    return puzzle;
}

class PuzzleQueue
{
public:
    explicit PuzzleQueue(size_t capacity) : capacity_(capacity) {}

    bool push(vector<Piece>&& puzzle)
    {
        unique_lock<mutex> lock(mutex_);
        not_full_.wait(lock, [&] { return closed_ || queue_.size() < capacity_; });

        if (closed_)
            return false;

        queue_.push_back(move(puzzle));
        not_empty_.notify_one();
        return true;
    }

    bool pop(vector<Piece>& puzzle)
    {
        unique_lock<mutex> lock(mutex_);
        not_empty_.wait(lock, [&] { return closed_ || !queue_.empty(); });

        if (queue_.empty())
            return false;

        puzzle = move(queue_.front());
        queue_.pop_front();
        not_full_.notify_one();
        return true;
    }

    void close()
    {
        {
            lock_guard<mutex> lock(mutex_);
            closed_ = true;
        }

        not_empty_.notify_all();
        not_full_.notify_all();
    }

private:
    size_t capacity_;
    deque<vector<Piece>> queue_;
    mutex mutex_;
    condition_variable not_empty_;
    condition_variable not_full_;
    bool closed_ = false;
};

struct PuzzleContext
{
    int n;
    vector<Piece> pieces;
    vector<array<Piece, 4>> rotations;
    vector<Candidate> all_candidates;
    array<vector<Candidate>, EDGE_INDEX_COUNT> by_top;
    array<vector<Candidate>, EDGE_INDEX_COUNT> by_left;
    array<vector<Candidate>, EDGE_INDEX_COUNT * EDGE_INDEX_COUNT> by_top_left;

    PuzzleContext(int size, vector<Piece> input)
        : n(size), pieces(move(input)), rotations(pieces.size())
    {
        build();
    }

    void build()
    {
        all_candidates.reserve(pieces.size() * 4);

        for (int id = 0; id < static_cast<int>(pieces.size()); ++id)
        {
            rotations[id][0] = pieces[id];
            for (int rot = 1; rot < 4; ++rot)
                rotations[id][rot] = rotate90(rotations[id][rot - 1]);

            for (int rot = 0; rot < 4; ++rot)
            {
                bool duplicate_rotation = false;

                for (int earlier = 0; earlier < rot; ++earlier)
                {
                    if (rotations[id][rot] == rotations[id][earlier])
                    {
                        duplicate_rotation = true;
                        break;
                    }
                }

                if (duplicate_rotation)
                    continue;

                const Candidate candidate{id, static_cast<uint8_t>(rot)};
                const Piece& piece = rotations[id][rot];
                all_candidates.push_back(candidate);
                by_top[edge_index(piece[0])].push_back(candidate);
                by_left[edge_index(piece[3])].push_back(candidate);
                by_top_left[edge_index(piece[0]) * EDGE_INDEX_COUNT + edge_index(piece[3])]
                    .push_back(candidate);
            }
        }
    }
};

struct SearchState
{
    vector<Cell> board;
    vector<uint8_t> used;
    unsigned long long nodes = 0;
};

const vector<Candidate>& matching_candidates(
    const PuzzleContext& context,
    const SearchState& state,
    int pos)
{
    static const vector<Candidate> empty;
    const int row = pos / context.n;
    const int col = pos % context.n;

    if (pos == 0)
        return context.all_candidates;

    if (row == 0)
    {
        const Cell& left = state.board[pos - 1];
        const int required_left = -context.rotations[left.id][left.rot][1];
        return context.by_left[edge_index(required_left)];
    }

    if (col == 0)
    {
        const Cell& top = state.board[pos - context.n];
        const int required_top = -context.rotations[top.id][top.rot][2];
        return context.by_top[edge_index(required_top)];
    }

    const Cell& top = state.board[pos - context.n];
    const Cell& left = state.board[pos - 1];
    const int required_top = -context.rotations[top.id][top.rot][2];
    const int required_left = -context.rotations[left.id][left.rot][1];
    return context.by_top_left[
        edge_index(required_top) * EDGE_INDEX_COUNT + edge_index(required_left)];
}

vector<uint32_t> canonical_solution(
    const PuzzleContext& context,
    const vector<Cell>& board)
{
    vector<uint32_t> best;
    best.reserve(board.size());

    for (int turn = 0; turn < 4; ++turn)
    {
        vector<uint32_t> key;
        key.reserve(board.size());

        for (int row = 0; row < context.n; ++row)
        {
            for (int col = 0; col < context.n; ++col)
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
                    source_row = context.n - 1 - col;
                    source_col = row;
                }
                else if (turn == 2)
                {
                    source_row = context.n - 1 - row;
                    source_col = context.n - 1 - col;
                }
                else
                {
                    source_row = col;
                    source_col = context.n - 1 - row;
                }

                const Cell& cell = board[source_row * context.n + source_col];
                const Piece& piece = context.rotations[cell.id][(cell.rot + turn) % 4];
                key.push_back(
                    (static_cast<uint32_t>(cell.id) << 12) |
                    static_cast<uint32_t>(encode_piece(piece)));
            }
        }

        if (turn == 0 || key < best)
            best = move(key);
    }

    return best;
}

struct SharedSearch
{
    atomic<int> next_branch{0};
    atomic<bool> reject{false};
    mutex solution_mutex;
    unsigned long long raw_solutions = 0;
    vector<uint32_t> first_canonical;
    vector<Cell> saved_solution;
};

bool record_solution(
    const PuzzleContext& context,
    const SearchState& state,
    SharedSearch& shared,
    const atomic<bool>& external_stop)
{
    lock_guard<mutex> lock(shared.solution_mutex);

    if (shared.reject.load(memory_order_relaxed) ||
        external_stop.load(memory_order_relaxed))
        return true;

    ++shared.raw_solutions;

    if (shared.raw_solutions > 4)
    {
        shared.reject.store(true, memory_order_release);
        return true;
    }

    vector<uint32_t> canonical = canonical_solution(context, state.board);

    if (shared.first_canonical.empty())
    {
        shared.first_canonical = move(canonical);
        shared.saved_solution = state.board;
    }
    else if (canonical != shared.first_canonical)
    {
        shared.reject.store(true, memory_order_release);
        return true;
    }

    return false;
}

bool dfs(
    const PuzzleContext& context,
    SearchState& state,
    int pos,
    SharedSearch& shared,
    const atomic<bool>& external_stop,
    atomic<unsigned long long>& interval_nodes)
{
    if (shared.reject.load(memory_order_acquire) ||
        external_stop.load(memory_order_relaxed))
        return true;

    ++state.nodes;
    if ((state.nodes & 4095ULL) == 0)
    {
        interval_nodes.fetch_add(4096ULL, memory_order_relaxed);
        state.nodes = 0;
    }

    if (pos == context.n * context.n)
        return record_solution(context, state, shared, external_stop);

    for (const Candidate& candidate : matching_candidates(context, state, pos))
    {
        if (shared.reject.load(memory_order_relaxed) ||
            external_stop.load(memory_order_relaxed))
            return true;

        if (state.used[candidate.id])
            continue;

        state.board[pos] = {candidate.id, candidate.rot};
        state.used[candidate.id] = 1;

        if (dfs(context, state, pos + 1, shared, external_stop, interval_nodes))
        {
            state.used[candidate.id] = 0;
            return true;
        }

        state.used[candidate.id] = 0;
    }

    return false;
}

SearchResult solve_puzzle(
    const PuzzleContext& context,
    int thread_count,
    const atomic<bool>& external_stop,
    atomic<unsigned long long>& interval_nodes)
{
    SharedSearch shared;
    const int branch_count = static_cast<int>(context.all_candidates.size());
    thread_count = max(1, min(thread_count, branch_count));
    auto worker = [&]()
    {
        SearchState state{
            vector<Cell>(static_cast<size_t>(context.n) * context.n),
            vector<uint8_t>(context.pieces.size(), 0),
            0};

        while (!shared.reject.load(memory_order_acquire) &&
               !external_stop.load(memory_order_relaxed))
        {
            const int branch = shared.next_branch.fetch_add(1, memory_order_relaxed);
            if (branch >= branch_count)
                break;

            fill(state.used.begin(), state.used.end(), 0);
            const Candidate first = context.all_candidates[branch];
            state.board[0] = {first.id, first.rot};
            state.used[first.id] = 1;
            dfs(context, state, 1, shared, external_stop, interval_nodes);
        }

        if (state.nodes != 0)
            interval_nodes.fetch_add(state.nodes, memory_order_relaxed);
    };

    vector<thread> workers;
    workers.reserve(max(0, thread_count - 1));

    for (int i = 1; i < thread_count; ++i)
        workers.emplace_back(worker);

    worker();

    for (thread& thread : workers)
        thread.join();


    const bool aborted = external_stop.load(memory_order_relaxed);
    const bool valid =
        !aborted &&
        !shared.reject.load(memory_order_acquire) &&
        shared.raw_solutions == 4 &&
        !shared.first_canonical.empty();

    return {
        valid,
        aborted,
        shared.raw_solutions,
        move(shared.saved_solution)};
}

void generator_worker(int n, PuzzleQueue& queue, uint64_t seed)
{
    mt19937_64 rng(seed);

    while (true)
    {
        vector<Piece> puzzle = generate_scrambled_puzzle(n, rng);
        if (!queue.push(move(puzzle)))
            return;
    }
}

void print_puzzle(const vector<Piece>& puzzle)
{
    for (const Piece& piece : puzzle)
        cout << piece[0] << ' ' << piece[1] << ' ' << piece[2] << ' ' << piece[3] << '\n';
}

void print_solution(const vector<Cell>& solution, int n)
{
    for (int row = 0; row < n; ++row)
    {
        for (int col = 0; col < n; ++col)
        {
            const Cell& cell = solution[row * n + col];
            cout << cell.id << '(' << static_cast<int>(cell.rot) << ')';
            if (col + 1 < n)
                cout << ' ';
        }
        cout << '\n';
    }
}

unsigned int parse_positive(const char* text)
{
    try
    {
        const unsigned long value = stoul(text);
        return value == 0 ? 0 : static_cast<unsigned int>(value);
    }
    catch (...)
    {
        return 0;
    }
}

int main(int argc, char* argv[])
{
    int n = 0;

    if (argc >= 2)
        n = static_cast<int>(parse_positive(argv[1]));
    else
    {
        cout << "Puzzle size: ";
        cin >> n;
    }

    if (n < 2 || static_cast<long long>(n) * n > MAX_UNIQUE_PIECES)
        return 1;

    unsigned int total_threads = thread::hardware_concurrency();
    if (total_threads == 0)
        total_threads = 2;

    if (argc >= 3)
    {
        const unsigned int requested = parse_positive(argv[2]);
        if (requested == 0)
            return 1;
        total_threads = requested;
    }

    total_threads = max(2u, total_threads);

    const int generator_threads = 1;
    const int solver_budget = max(1, static_cast<int>(total_threads) - generator_threads);
    const int solver_groups = min(
        MAX_CONCURRENT_PUZZLES,
        max(1, (solver_budget + TARGET_THREADS_PER_PUZZLE - 1) /
                   TARGET_THREADS_PER_PUZZLE));

    vector<int> group_threads(solver_groups, solver_budget / solver_groups);
    for (int i = 0; i < solver_budget % solver_groups; ++i)
        ++group_threads[i];

    PuzzleQueue queue(static_cast<size_t>(solver_groups) * 3 + 2);
    atomic<bool> found{false};
    atomic<unsigned long long> checked{0};
    atomic<unsigned long long> interval_nodes{0};
    atomic<bool> reporting_done{false};
    mutex report_mutex;
    condition_variable report_cv;
    mutex winner_mutex;
    vector<Piece> winner_puzzle;
    SearchResult winner_result;
    unsigned long long winner_checked = 0;

    const auto start = chrono::steady_clock::now();

    thread reporter([&]
    {
        unique_lock<mutex> lock(report_mutex);
        auto previous = chrono::steady_clock::now();

        while (!reporting_done.load(memory_order_acquire))
        {
            if (report_cv.wait_for(
                    lock,
                    chrono::seconds(10),
                    [&] { return reporting_done.load(memory_order_acquire); }))
                break;

            const auto now = chrono::steady_clock::now();
            const double elapsed =
                chrono::duration<double>(now - previous).count();
            previous = now;

            const unsigned long long nodes =
                interval_nodes.exchange(0, memory_order_acq_rel);
            const unsigned long long puzzles =
                checked.load(memory_order_relaxed);
            const double rate = elapsed > 0.0 ? nodes / elapsed : 0.0;

            cout << "Puzzles checked: " << puzzles
                 << " | Nodes: " << nodes
                 << " | Nodes/s: " << fixed << setprecision(0)
                 << rate << '\n' << flush;
        }
    });

    random_device rd;
    const uint64_t base_seed =
        (static_cast<uint64_t>(rd()) << 32) ^
        static_cast<uint64_t>(chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<thread> generators;
    generators.reserve(generator_threads);

    for (int i = 0; i < generator_threads; ++i)
        generators.emplace_back(generator_worker, n, ref(queue), base_seed + i * 0x9E3779B97F4A7C15ULL);

    vector<thread> solver_workers;
    solver_workers.reserve(solver_groups);

    for (int group = 0; group < solver_groups; ++group)
    {
        solver_workers.emplace_back([&, group]
        {
            vector<Piece> puzzle;

            while (!found.load(memory_order_acquire) && queue.pop(puzzle))
            {
                PuzzleContext context(n, puzzle);
                SearchResult result =
                    solve_puzzle(context, group_threads[group], found, interval_nodes);

                if (result.aborted)
                    break;

                const unsigned long long completed =
                    checked.fetch_add(1, memory_order_relaxed) + 1;

                if (!result.valid)
                    continue;

                bool expected = false;
                if (found.compare_exchange_strong(
                        expected,
                        true,
                        memory_order_acq_rel))
                {
                    {
                        lock_guard<mutex> lock(winner_mutex);
                        winner_puzzle = move(puzzle);
                        winner_result = move(result);
                        winner_checked = completed;
                    }
                    queue.close();
                }

                break;
            }
        });
    }

    for (thread& worker : solver_workers)
        worker.join();

    queue.close();

    for (thread& generator : generators)
        generator.join();

    reporting_done.store(true, memory_order_release);
    report_cv.notify_one();
    reporter.join();

    if (!found.load(memory_order_acquire))
        return 0;

    const double seconds = chrono::duration<double>(
        chrono::steady_clock::now() - start).count();

    cout << "\nFound\n";
    cout << "Checked: " << winner_checked << '\n';
    cout << "Raw solutions: " << winner_result.raw_solutions << '\n';
    cout << "CPU threads: " << total_threads << '\n';
    cout << "Concurrent puzzles: " << solver_groups << '\n';
    cout << "Seconds: " << seconds << "\n\n";
    cout << "Puzzle:\n";
    print_puzzle(winner_puzzle);
    cout << "\nRepresentative solution:\n";
    print_solution(winner_result.solution, n);

    return 0;
}
