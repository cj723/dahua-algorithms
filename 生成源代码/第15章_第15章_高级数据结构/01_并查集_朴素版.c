#include <stdio.h>

#define MAXN 100010

int parent[MAXN]; // parent[i] 表示元素 i 的"帮派代表"

// 初始化：每个人自成一派
void init(int n) {
    for (int i = 1; i <= n; i++) {
        parent[i] = i;  // 自己当自己的老大
    }
}

// 查找：找到 x属于哪个帮派（返回帮派代表）
int find(int x) {
    while (parent[x] != x) {
        x = parent[x];  // 顺着链条往上找
    }
    return x;
}

// 合并：把 x 和 y 所在的帮派合并
void unite(int x, int y) {
    int rx = find(x);
    int ry = find(y);
    if (rx != ry) {
        parent[rx] = ry;  // x 的老大认y 的老大当老大
    }
}

// 判断：x 和 y 是不是一伙的
int is_same(int x, int y) {
    return find(x) == find(y);
}


// 测试：最朴素的并查集
int main(void) {
    init(6);  // 6 个元素：1～6

    unite(1, 2);
    unite(2, 3);
    unite(4, 5);

    printf("1 和 3 是一伙的吗？%s\n", is_same(1, 3) ? "是" : "不是");
    printf("1 和 4 是一伙的吗？%s\n", is_same(1, 4) ? "是" : "不是");

    unite(3, 4);
    printf("合并 3 和 4 后，1 和 5 是一伙的吗？%s\n", is_same(1, 5) ? "是" : "不是");

    return 0;
}