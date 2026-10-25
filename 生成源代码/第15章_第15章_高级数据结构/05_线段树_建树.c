#include <stdio.h>

#define MAXN 100010

int a[MAXN];       // 原数组
long long tree[4 * MAXN];  // 线段树

// 建树：当前节点编号 p，管理区间[l, r]
void build(int p, int l, int r) {
    if (l == r) {
        tree[p] = a[l];  // 叶子节点，直接存值
        return;
    }
    int mid = l + (r - l) / 2;
    build(2 * p, l, mid);        // 建左子树
    build(2 * p + 1, mid + 1, r); // 建右子树
    tree[p] = tree[2 * p] + tree[2 * p + 1];  // 区间和 = 左+右
}


int main(void) {
    int n = 8;
    int d[] = {3, 1, 4, 1, 5, 9, 2, 6};

    for (int i = 1; i <= n; i++) {
        a[i] = d[i - 1];
    }

    printf("线段树建树演示：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：3 1 4 1 5 9 2 6\n");
    build(1, 1, n);
    printf("根节点 tree[1] 保存整个区间[1,%d]的和：%lld\n", n, tree[1]);
    printf("左半区[1, 4] tree[2] = %lld，右半区[5, 8] tree[3] = %lld\n", tree[2], tree[3]);

    return 0;
}
