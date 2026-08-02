#include <array>
#include <ctime>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using namespace std;

int n;

struct Edge
{
    int value;
};

struct Piece
{
    Edge e[4]; // top, right, bottom, left
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

struct PairHash
{
    size_t operator()(const pair<int, int> &key) const noexcept
    {
        size_t h1 = hash<int>{}(key.first);
        size_t h2 = hash<int>{}(key.second);
        return h1 ^ (h2 << 1);
    }
};

vector<Piece> pieces;
vector<array<Piece, 4>> rotations;
vector<Cell> board;
vector<char> used;

vector<Candidate> allCandidates;
unordered_map<int, vector<Candidate>> topDictionary;
unordered_map<int, vector<Candidate>> leftDictionary;
unordered_map<pair<int, int>, vector<Candidate>, PairHash> topLeftDictionary;

long long nodes = 0;

Piece rotate90(const Piece &p)
{
    Piece q;

    q.e[0] = p.e[3];
    q.e[1] = p.e[0];
    q.e[2] = p.e[1];
    q.e[3] = p.e[2];

    return q;
}

void buildDictionaries()
{
    int pieceCount = n * n;

    rotations.resize(pieceCount);

    for (int id = 0; id < pieceCount; id++)
    {
        rotations[id][0] = pieces[id];

        for (int r = 1; r < 4; r++)
            rotations[id][r] = rotate90(rotations[id][r - 1]);

        for (int r = 0; r < 4; r++)
        {
            Candidate candidate{id, r};
            int top = rotations[id][r].e[0].value;
            int left = rotations[id][r].e[3].value;

            allCandidates.push_back(candidate);
            topDictionary[top].push_back(candidate);
            leftDictionary[left].push_back(candidate);
            topLeftDictionary[{top, left}].push_back(candidate);
        }
    }
}

bool dfs(int pos)
{
    nodes++;

    if (pos == n * n)
        return true;

    int row = pos / n;
    int col = pos % n;

    const vector<Candidate> *candidates;

    if (row == 0 && col == 0)
    {
        candidates = &allCandidates;
    }
    else if (row == 0)
    {
        int requiredLeft = -board[pos - 1].p.e[1].value;
        auto it = leftDictionary.find(requiredLeft);

        if (it == leftDictionary.end())
            return false;

        candidates = &it->second;
    }
    else if (col == 0)
    {
        int requiredTop = -board[pos - n].p.e[2].value;
        auto it = topDictionary.find(requiredTop);

        if (it == topDictionary.end())
            return false;

        candidates = &it->second;
    }
    else
    {
        int requiredTop = -board[pos - n].p.e[2].value;
        int requiredLeft = -board[pos - 1].p.e[1].value;
        auto it = topLeftDictionary.find({requiredTop, requiredLeft});

        if (it == topLeftDictionary.end())
            return false;

        candidates = &it->second;
    }

    for (const Candidate &candidate : *candidates)
    {
        int id = candidate.id;
        int r = candidate.rot;

        if (used[id])
            continue;

        board[pos].id = id;
        board[pos].rot = r;
        board[pos].p = rotations[id][r];

        used[id] = true;

        if (dfs(pos + 1))
            return true;

        used[id] = false;
    }

    return false;
}

int main()
{
    cout << "Enter puzzle size n: ";
    cin >> n;
    cin.ignore(numeric_limits<streamsize>::max(), '\n');

    if (n <= 0)
    {
        cerr << "Invalid puzzle size\n";
        return 1;
    }

    string filename;
    cout << "Enter the full path of the puzzle file:\n> ";
    getline(cin, filename);

    ifstream input(filename);

    if (!input)
    {
        cerr << "Cannot open file: " << filename << '\n';
        return 1;
    }

    int pieceCount = n * n;

    pieces.resize(pieceCount);
    board.resize(pieceCount);
    used.assign(pieceCount, false);

    for (int id = 0; id < pieceCount; id++)
    {
        for (int side = 0; side < 4; side++)
        {
            if (!(input >> pieces[id].e[side].value))
            {
                cerr << "Not enough puzzle data\n";
                return 1;
            }
        }
    }

    buildDictionaries();

    clock_t start = clock();
    bool solved = dfs(0);
    clock_t end = clock();

    if (solved)
    {
        cout << "\nSolved!\n\n";

        for (int row = 0; row < n; row++)
        {
            for (int col = 0; col < n; col++)
            {
                const Cell &cell = board[row * n + col];
                cout << cell.id << "(" << cell.rot << ") ";
            }

            cout << '\n';
        }
    }
    else
    {
        cout << "\nNo solution\n";
    }

    cout << "\nTime: "
         << 1000.0 * (end - start) / CLOCKS_PER_SEC
         << " ms\n";
    cout << "Tries: " << nodes << '\n';

    return 0;
}
