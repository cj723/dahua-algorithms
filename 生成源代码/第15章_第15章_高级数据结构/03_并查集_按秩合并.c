#include <stdio.h>

#define MAXN 100010

int parent[MAXN];
int rank_[MAXN];  // 变量名加下划线是为了代码可读性，避免与可能的 rank() 函数混淆

void init(int n) {
    for (int i = 1; i <= n; i++) {
        parent[i] = i;
        rank_[i] = 0;  // 初始高度都是 0
    }
}

int find(int x) {
    if (parent[x] != x) {
        parent[x] = find(parent[x]);  // 路径压缩
    }
    return parent[x];
}

void unite(int x, int y) {
    int rx = find(x);
    int ry = find(y);
    if (rx == ry) return;  // 已经是一伙的了
    
    // 按秩合并：小树挂到大树上
    if (rank_[rx] < rank_[ry]) {
        parent[rx] = ry;       // rx 矮，挂到 ry下面
    } else if (rank_[rx] > rank_[ry]) {
        parent[ry] = rx;       // ry 矮，挂到 rx下面
    } else {
        parent[ry] = rx;       // 一样高，随便挂，被挂的那个高度 + 1
        rank_[rx]++;
    }
}

int is_same(int x, int y) {
    return find(x) == find(y);
}


// 测试：按秩合并 + 路径压缩
int main(void) {
    init(6);

    unite(1, 2); unite(3, 4); unite(5, 6);
    printf("初始帮派：{1,2} {3,4} {5,6}\n");

    unite(1, 3);
    printf("合并 1 和 3 后：1 和 4 一伙？%s\n", is_same(1, 4) ? "是" : "不是");

    unite(1, 5);
    printf("合并 1 和 5 后：2 和 6 一伙？%s\n", is_same(2, 6) ? "是" : "不是");

    printf("\n按秩合并确保了树的高度始终 ≤ log n，保证了效率\n");

    return 0;
}