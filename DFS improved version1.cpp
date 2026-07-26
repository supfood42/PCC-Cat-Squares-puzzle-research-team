#include <iostream>
#include <ctime>
#include <cmath>
#include <vector>
#include <unordered_map>

using namespace std;

const int N = 20;
int n = 20;

struct Piece
{
    int e[4];
};

struct Cell
{
    int id;
    int rot;
    Piece p;
};

Piece pieces[N * N];
Piece rot[N * N][4];

Cell board[N][N];

bool used[N * N];

long long nodes = 0;

unordered_map<int, vector<pair<int,int>>> edge_map;


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
        for (int r = 0; r < 4; r++)
        {
            for (int e = 0; e < 4; e++)
            {
                int val = rot[i][r].e[e];
                edge_map[val].push_back({i, r});
            }
        }
    }
}

bool dfs(int pos)
{
    nodes++;

    if (pos == n * n)
        return true;

    int r = pos / n;
    int c = pos % n;

    vector<pair<int,int>> candidates;

    if (r > 0)
    {
        int need = -board[r - 1][c].p.e[2];
        candidates = edge_map[need];
    }
    else if (c > 0)
    {
        int need = -board[r][c - 1].p.e[1];
        candidates = edge_map[need];
    }
    else
    {
        for (int i = 0; i < n * n; i++)
            for (int k = 0; k < 4; k++)
                candidates.push_back({i, k});
    }

    for (auto &pr : candidates)
    {
        int i = pr.first;
        int k = pr.second;

        if (used[i]) continue;

        Piece &p = rot[i][k];

        if (r > 0 && p.e[0] + board[r - 1][c].p.e[2] != 0)
            continue;

        if (c > 0 && p.e[3] + board[r][c - 1].p.e[1] != 0)
            continue;

        board[r][c].id = i;
        board[r][c].rot = k;
        board[r][c].p = p;

        used[i] = true;

        if (dfs(pos + 1))
            return true;

        used[i] = false;
    }

    return false;
}


int main()
{
    clock_t start = clock();

    cout << "Puzzle size = " << n << "x" << '\n';
    cout << "Enter " << n * n << " pieces:\n";
    cout << "Each piece: 4 integers (positive/negative)\n\n";

    for (int i = 0; i < n * n; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            cin >> pieces[i].e[j];
        }
    }

    for (int i = 0; i < n * n; i++)
        used[i] = false;

    build_rotations();
    build_index();

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
