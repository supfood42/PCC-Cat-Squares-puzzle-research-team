#include <iostream>
#include <ctime>
#include <cmath>

using namespace std;

const int N = 5;

int n = 5;

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

Piece pieces[N * N];
Piece rot[N * N][4];

Cell board[N][N];

bool used[N * N];

long long nodes = 0;
long long solutions = 0;

time_t start;

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

void dfs(int pos)
{
    nodes++;

    if (pos == n * n)
    {
        solutions++;

        if (solutions % 40 == 0)
        {
            time_t now = time(NULL);

            cout << "Solutions found: "
                 << solutions
                 << "    Time: "
                 << difftime(now, start)
                 << " s"
                 << '\n';
        }

        return;
    }

    int r = pos / n;
    int c = pos % n;

    for (int i = 0; i < n * n; i++)
    {
        if (used[i])
            continue;

        for (int k = 0; k < 4; k++)
        {
            board[r][c].id = i;
            board[r][c].rot = k;
            board[r][c].p = rot[i][k];

            if (valid(r, c))
            {
                used[i] = true;

                dfs(pos + 1);

                used[i] = false;
            }
        }
    }
}

int main()
{
    start = time(NULL);

    cout << "Puzzle size = " << n << "x" << '\n';
    cout << "Enter " << n * n << " pieces:\n";
    cout << "Each piece: 4 integers (positive/negative)\n\n";

    for (int i = 0; i < n * n; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            cin >> pieces[i].e[j].value;
        }
    }

    for (int i = 0; i < n * n; i++)
    {
        used[i] = false;
    }

    build_rotations();

    dfs(0);

    if (solutions == 0)
    {
        cout << "\nNo solution\n";
    }
    else
    {
        cout << "\nTotal Solutions: "
             << solutions
             << '\n';
    }

    time_t end = time(NULL);

    cout << "\nTotal Time: "
         << difftime(end, start)
         << " s\n";

    cout << "Tries: "
         << nodes
         << '\n';

    return 0;
}