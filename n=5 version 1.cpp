#include <iostream>
#include <ctime>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <string>

using namespace std;

const int N = 10;

int n = 10;

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

Piece pieces[N * N];
Piece rot[N * N][4];

Cell board[N][N];

bool used[N * N];

unordered_map<int, vector<Candidate> > top_index;
unordered_map<int, vector<Candidate> > left_index;

long long nodes = 0;

bool match(Edge a, Edge b)
{
    return abs(a.value) == abs(b.value) &&
           a.value + b.value == 0;
}

Piece rotate90(Piece p)
{
    Piece q;

    q.e[0] = p.e[3];
    q.e[1] = p.e[0];
    q.e[2] = p.e[1];
    q.e[3] = p.e[2];

    return q;
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

void build_index()
{
    for (int i = 0; i < n * n; i++)
    {
        for (int k = 0; k < 4; k++)
        {
            Candidate candidate;

            candidate.id = i;
            candidate.rot = k;

            int top_color = abs(rot[i][k].e[0].value);
            int left_color = abs(rot[i][k].e[3].value);

            top_index[top_color].push_back(candidate);
            left_index[left_color].push_back(candidate);
        }
    }
}

bool valid(int r, int c)
{
    Piece &cur = board[r][c].p;

    if (r > 0)
    {
        if (!match(cur.e[0], board[r - 1][c].p.e[2]))
            return false;
    }

    if (c > 0)
    {
        if (!match(cur.e[3], board[r][c - 1].p.e[1]))
            return false;
    }

    return true;
}

bool dfs(int pos);

bool try_candidate(int pos, int r, int c, Candidate candidate)
{
    int i = candidate.id;
    int k = candidate.rot;

    if (used[i])
        return false;

    board[r][c].id = i;
    board[r][c].rot = k;
    board[r][c].p = rot[i][k];

    if (!valid(r, c))
        return false;

    used[i] = true;

    if (dfs(pos + 1))
        return true;

    used[i] = false;

    return false;
}

bool dfs(int pos)
{
    nodes++;

    if (pos == n * n)
        return true;

    int r = pos / n;
    int c = pos % n;

    if (r == 0 && c == 0)
    {
        for (int i = 0; i < n * n; i++)
        {
            for (int k = 0; k < 4; k++)
            {
                Candidate candidate;

                candidate.id = i;
                candidate.rot = k;

                if (try_candidate(pos, r, c, candidate))
                    return true;
            }
        }

        return false;
    }

    vector<Candidate> *candidates;

    if (r > 0 && c > 0)
    {
        int top_color = abs(board[r - 1][c].p.e[2].value);
        int left_color = abs(board[r][c - 1].p.e[1].value);

        vector<Candidate> &top_candidates = top_index[top_color];
        vector<Candidate> &left_candidates = left_index[left_color];

        if (top_candidates.size() < left_candidates.size())
            candidates = &top_candidates;
        else
            candidates = &left_candidates;
    }
    else if (r > 0)
    {
        int top_color = abs(board[r - 1][c].p.e[2].value);

        candidates = &top_index[top_color];
    }
    else
    {
        int left_color = abs(board[r][c - 1].p.e[1].value);

        candidates = &left_index[left_color];
    }

    for (size_t i = 0; i < candidates->size(); i++)
    {
        if (try_candidate(pos, r, c, (*candidates)[i]))
            return true;
    }

    return false;
}

int main()
{
    cout << "Puzzle size = " << n << "x" << '\n';
    cout << "Enter input file path:\n";

    string file_path;

    getline(cin, file_path);

    ifstream input_file(file_path);

    if (!input_file)
    {
        cout << "\nCannot open input file\n";
        return 1;
    }

    for (int i = 0; i < n * n; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            if (!(input_file >> pieces[i].e[j].value))
            {
                cout << "\nInvalid input file\n";
                cout << "The file must contain "
                     << n * n
                     << " pieces, each with 4 integers\n";

                return 1;
            }
        }
    }

    for (int i = 0; i < n * n; i++)
        used[i] = false;

    build_rotations();
    build_index();

    clock_t start = clock();

    if (dfs(0))
    {
        cout << "\nSolved!\n\n";

        for (int i = 0; i < n; i++)
        {
            for (int j = 0; j < n; j++)
            {
                cout << board[i][j].id
                     << "("
                     << board[i][j].rot
                     << ") ";
            }

            cout << '\n';
        }
    }
    else
    {
        cout << "\nNo solution\n";
    }

    clock_t end = clock();

    cout << "\nTime: "
         << 1000.0 * (end - start) / CLOCKS_PER_SEC
         << " ms\n";

    cout << "Tries: " << nodes << '\n';

    return 0;
}
