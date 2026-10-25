#include <stdio.h>

#define MAXN 100010

int parent[MAXN], rank_[MAXN];

void init(int n) {
    for (int i = 1; i <= n; i++) {
        parent[i] = i;
        rank_[i] = 0;
    }
}

int find(int x) {
    if (parent[x] != x) {
        parent[x] = find(parent[x]);
    }
    return parent[x];
}

void unite(int x, int y) {
    int rx = find(x), ry = find(y);
    if (rx == ry) return;
    if (rank_[rx] < rank_[ry]) {
        parent[rx] = ry;
    } else if (rank_[rx] > rank_[ry]) {
        parent[ry] = rx;
    } else {
        parent[ry] = rx;
        rank_[rx]++;
    }
}

int is_same(int x, int y) {
    return find(x) == find(y);
}

int main(void) {
    // 固定测试数据，便于直接运行观察结果
    init(4);
    printf("社交圈测试（4人）:\n");

    unite(1, 2); printf("1 和 2 成为朋友\n");
    unite(2, 3); printf("2 和 3 成为朋友\n");
    printf("1 和 3 是一伙的吗？%s\n", is_same(1, 3) ? "Yes" : "No");
    printf("1 和 4 是一伙的吗？%s\n", is_same(1, 4) ? "Yes" : "No");
    return 0;
}
