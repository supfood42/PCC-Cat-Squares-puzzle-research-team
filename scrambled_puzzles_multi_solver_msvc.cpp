#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <regex>
#include <stdexcept>
#include <string>
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

vector<Piece> pieces;
vector<array<Piece, 4>> rot;
vector<vector<Cell>> board;
vector<bool> used;
long long nodes = 0;

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

const vector<Candidate>& matching_candidates(int r, int c)
{
    static const vector<Candidate> empty;

    if (r == 0 && c == 0)
        return all_candidates;

    if (r == 0)
    {
        int required_left = -board[r][c - 1].p.e[1].value;
        auto it = by_left.find(required_left);
        return it == by_left.end() ? empty : it->second;
    }

    if (c == 0)
    {
        int required_top = -board[r - 1][c].p.e[2].value;
        auto it = by_top.find(required_top);
        return it == by_top.end() ? empty : it->second;
    }

    int required_top = -board[r - 1][c].p.e[2].value;
    int required_left = -board[r][c - 1].p.e[1].value;
    auto it = by_top_left.find(edge_pair_key(required_top, required_left));
    return it == by_top_left.end() ? empty : it->second;
}

bool dfs(int pos)
{
    nodes++;

    if (pos == n * n)
        return true;

    int r = pos / n;
    int c = pos % n;

    const vector<Candidate>& candidates = matching_candidates(r, c);

    for (const Candidate& candidate : candidates)
    {
        if (used[candidate.id])
            continue;

        board[r][c].id = candidate.id;
        board[r][c].rot = candidate.rot;
        board[r][c].p = rot[candidate.id][candidate.rot];

        used[candidate.id] = true;

        if (dfs(pos + 1))
            return true;

        used[candidate.id] = false;
    }

    return false;
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
    board.assign(n, vector<Cell>(n));
    used.assign(n * n, false);
    nodes = 0;

    build_rotations();
    build_lookup();
}

void print_solution()
{
    for (int r = 0; r < n; r++)
    {
        for (int c = 0; c < n; c++)
        {
            cout << board[r][c].id
                 << "("
                 << board[r][c].rot
                 << ") ";
        }

        cout << '\n';
    }
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
            string input_path;
            getline(cin, input_path);
            file_path = input_path;
        }

        const FileInfo file_info = parse_filename(file_path);
        n = file_info.size;

        const vector<vector<Piece>> puzzles =
            load_puzzles(file_path, file_info.puzzle_count);

        cout << "\nLoaded " << file_info.puzzle_count
             << " puzzles of size " << n << "x" << n << ".\n";

        int solved_count = 0;
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
            const bool solved = dfs(0);
            const auto puzzle_end = chrono::steady_clock::now();

            const double elapsed_ms =
                chrono::duration<double, milli>(
                    puzzle_end - puzzle_start).count();

            if (solved)
            {
                solved_count++;
                cout << "Solved!\n\n";
                print_solution();
            }
            else
            {
                cout << "No solution\n";
            }

            cout << fixed << setprecision(3);
            cout << "\nTime: " << elapsed_ms << " ms\n";
            cout << "Tries: " << nodes << '\n';
        }

        const auto total_end = chrono::steady_clock::now();
        const double total_ms =
            chrono::duration<double, milli>(
                total_end - total_start).count();

        cout << "\n========================================\n";
        cout << "Finished all puzzles\n";
        cout << "Solved: " << solved_count
             << " / " << file_info.puzzle_count << '\n';
        cout << "Total time: " << total_ms << " ms\n";
        cout << "Average time: "
             << total_ms / file_info.puzzle_count
             << " ms per puzzle\n";

        return 0;
    }
    catch (const exception& error)
    {
        cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
