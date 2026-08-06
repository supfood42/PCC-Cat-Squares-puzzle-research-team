#include <iostream>
#include <ctime>
#include <cmath>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <string>

using namespace std;

const int N = 32; // 修改为 6x6
int n = 32;

struct Edge {
    int value;    
};

struct Piece {
    Edge e[4]; // 0: Top, 1: Right, 2: Bottom, 3: Left
};

struct Cell {
    int id;
    int rot;
    Piece p;
};

struct Candidate {
    int id;
    int rot;
};

Piece pieces[N * N];
Piece rot[N * N][4];
Cell board[N][N];
bool used[N * N];

// 哈希表 Key 直接用边的真实数值（带有正负号）
unordered_map<int, vector<Candidate>> top_index;  // Key 为拼块 Top 边的值
unordered_map<int, vector<Candidate>> left_index; // Key 为拼块 Left 边的值

long long nodes = 0;

bool match(Edge a, Edge b) {
    return a.value + b.value == 0; // 互为相反数即匹配
}

Piece rotate90(Piece p) {
    Piece q;
    q.e[0] = p.e[3];
    q.e[1] = p.e[0];
    q.e[2] = p.e[1];
    q.e[3] = p.e[2];
    return q;
}

void build_rotations() {
    for (int i = 0; i < n * n; i++) {
        rot[i][0] = pieces[i];
        for (int r = 1; r < 4; r++)
            rot[i][r] = rotate90(rot[i][r - 1]);
    }
}

// 修正后的索引建立函数
void build_index() {
    top_index.clear();
    left_index.clear();
    for (int i = 0; i < n * n; i++) {
        for (int k = 0; k < 4; k++) {
            Candidate candidate = {i, k};
            
            // 直接记录真实带符号数值
            int top_val = rot[i][k].e[0].value;
            int left_val = rot[i][k].e[3].value;

            top_index[top_val].push_back(candidate);
            left_index[left_val].push_back(candidate);
        }
    }
}

// 修正 DFS 中的目标匹配逻辑
bool dfs(int pos) {
    nodes++;
    if (pos == n * n) return true;

    int r = pos / n;
    int c = pos % n;

    // (0,0) 位置尝试所有可能性
    if (r == 0 && c == 0) {
        for (int i = 0; i < n * n; i++) {
            for (int k = 0; k < 4; k++) {
                board[0][0].id = i;
                board[0][0].rot = k;
                board[0][0].p = rot[i][k];
                used[i] = true;

                if (dfs(pos + 1)) return true;

                used[i] = false;
            }
        }
        return false;
    }

    // 根据上邻居或左邻居计算当前拼块需要匹配的准确数值
    vector<Candidate>* candidates = nullptr;
    vector<Candidate> filtered_candidates;

    if (r > 0 && c > 0) {
        // 需要当前 Top == -target_top 且 当前 Left == -target_left
        int target_top = -board[r - 1][c].p.e[2].value;
        int target_left = -board[r][c - 1].p.e[1].value;

        // 取出符合 Top 的候选，再过滤符合 Left 的
        auto& top_cands = top_index[target_top];
        for (auto& cand : top_cands) {
            if (rot[cand.id][cand.rot].e[3].value == target_left) {
                filtered_candidates.push_back(cand);
            }
        }
        candidates = &filtered_candidates;
    }
    else if (r > 0) {
        int target_top = -board[r - 1][c].p.e[2].value;
        candidates = &top_index[target_top];
    }
    else {
        int target_left = -board[r][c - 1].p.e[1].value;
        candidates = &left_index[target_left];
    }

    for (auto& cand : *candidates) {
        int i = cand.id;
        int k = cand.rot;

        if (used[i]) continue;

        board[r][c].id = i;
        board[r][c].rot = k;
        board[r][c].p = rot[i][k];
        used[i] = true;

        if (dfs(pos + 1)) return true;

        used[i] = false;
    }

    return false;
}