#include <stdio.h>

#define MAXN 100010

int parent[MAXN];

void init(int n) {
    for (int i = 1; i <= n; i++) parent[i] = i;
}

// 路径压缩版 find：递归地把链条压扁
int find(int x) {
    if (parent[x] != x) {
        parent[x] = find(parent[x]);
    }
    return parent[x];
}

void unite(int x, int y) {
    int rx = find(x), ry = find(y);
    if (rx != ry) parent[rx] = ry;
}

// 测试：演示路径压缩的效果
int main(void) {
    init(5);

    // 故意构造一条长链：5→4→3→2→1
    parent[2] = 1; parent[3] = 2; parent[4] = 3; parent[5] = 4;

    printf("压缩前：parent[5]=%d, parent[4]=%d, parent[3]=%d\n",
           parent[5], parent[4], parent[3]);

    // find(5) 会触发路径压缩，把5直接挂到根节点1上
    find(5);
    printf("find(5) 后：parent[5]=%d（直接指向根！）\n", parent[5]);
    printf("路径压缩把链压成了星形，后续查询接近 O(1)\n");

    return 0;
}
