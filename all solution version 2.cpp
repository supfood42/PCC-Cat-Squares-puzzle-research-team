#include <iostream>
#include <ctime>
#include <cmath>
#include <atomic> // 必须引入原子变量，防止多线程竞争
#include <omp.h>  // 编译时需开启 -fopenmp

using namespace std;

const int N = 6;
int n = 6;

struct Edge { int value; };
struct Piece { Edge e[4]; };
struct Cell { int id; int rot; Piece p; };

Piece pieces[N * N];
Piece rot[N * N][4];

// 【多线程修改】：原子计数器，保证多线程下统计数量不会冲突
atomic<long long> nodes{0};
atomic<long long> solutions{0};
time_t start_time;

bool match(Edge a, Edge b) {
    return a.value + b.value == 0;
}

Piece rotate90(Piece p) {
    Piece q;
    q.e[0] = p.e[3]; q.e[1] = p.e[0];
    q.e[2] = p.e[1]; q.e[3] = p.e[2];
    return q;
}

void build_rotations() {
    for (int i = 0; i < n * n; i++) {
        rot[i][0] = pieces[i];
        for (int r = 1; r < 4; r++)
            rot[i][r] = rotate90(rot[i][r - 1]);
    }
}

bool valid(int r, int c, Cell board[N][N]) {
    Piece &cur = board[r][c].p;
    if (r > 0 && !match(cur.e[0], board[r - 1][c].p.e[2])) return false;
    if (c > 0 && !match(cur.e[3], board[r][c - 1].p.e[1])) return false;
    return true;
}

void print_solution(Cell board[N][N], long long sol_id) {
    // 使用 omp critical 保护输出，避免多个线程打印日志交织乱套
    #pragma omp critical
    {
        cout << "\n================ Solution #" << sol_id << " ================\n";
        for (int r = 0; r < n; r++) {
            for (int c = 0; c < n; c++) {
                cout << "[P";
                if (board[r][c].id < 10) cout << "0";
                cout << board[r][c].id << " r" << board[r][c].rot << "] ";
            }
            cout << '\n';
        }
        cout << "===============================================\n\n";
    }
}

// 【关键修改】：将 board 和 used 改为局部参数或按值传递，消除线程间的共享冲突
void dfs(int pos, Cell board[N][N], bool used[N * N]) {
    nodes++;

    if (pos == n * n) {
        long long current_sol = ++solutions;
        time_t now = time(NULL);
        
        #pragma omp critical
        {
            cout << "Found solution #" << current_sol 
                 << " | Time: " << difftime(now, start_time) << " s\n";
        }

        print_solution(board, current_sol);
        return;
    }

    int r = pos / n;
    int c = pos % n;

    for (int i = 0; i < n * n; i++) {
        if (used[i]) continue;

        int max_rot = (pos == 0) ? 1 : 4;

        for (int k = 0; k < max_rot; k++) {
            board[r][c].id = i;
            board[r][c].rot = k;
            board[r][c].p = rot[i][k];

            if (valid(r, c, board)) {
                used[i] = true;
                dfs(pos + 1, board, used);
                used[i] = false;
            }
        }
    }
}

// 并行入口：按 pos == 0 的第一块选择进行任务拆分
void solve_parallel() {
    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < n * n; i++) {
        // 每个线程拥有属于自己的板面和使用状态数组
        Cell local_board[N][N];
        bool local_used[N * N] = {false};

        // 绑定第 0 位置放置第 i 块拼图（固定旋转 0）
        local_board[0][0].id = i;
        local_board[0][0].rot = 0;
        local_board[0][0].p = rot[i][0];
        local_used[i] = true;

        // 线程独立深入搜索 pos == 1 之后的分支
        dfs(1, local_board, local_used);
    }
}

int main() {
    start_time = time(NULL);

    cout << "Puzzle size = " << n << "x" << n << '\n';
    cout << "Enter " << n * n << " pieces:\n";

    for (int i = 0; i < n * n; i++) {
        for (int j = 0; j < 4; j++) {
            cin >> pieces[i].e[j].value;
        }
    }

    build_rotations();

    cout << "Running with " << omp_get_max_threads() << " threads...\n";

    solve_parallel();

    if (solutions == 0) {
        cout << "\nNo solution found.\n";
    } else {
        cout << "\nTotal Unique Solutions: " << solutions << '\n';
    }

    time_t end = time(NULL);
    cout << "Total Time: " << difftime(end, start_time) << " s\n";
    cout << "Tries (nodes visited): " << nodes << '\n';

    return 0;
}
