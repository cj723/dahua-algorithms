#include <stdio.h>

#define MAXN 100010
long long tree[4 * MAXN];  // 线段树数组（4 倍空间）
long long a[MAXN];          // 原数组

// 建树
void build(int p, int l, int r) {
    if (l == r) { tree[p] = a[l]; return; }
    int mid = l + (r - l) / 2;
    build(2 * p, l, mid);
    build(2 * p + 1, mid + 1, r);
    tree[p] = tree[2 * p] + tree[2 * p + 1];
}

// 单点修改：把位置 x 的值加上 d
void update(int p, int l, int r, int x, long long d) {
    if (l == r) { tree[p] += d; return; }
    int mid = l + (r - l) / 2;
    if (x <= mid)
        update(2 * p, l, mid, x, d);
    else
        update(2 * p + 1, mid + 1, r, x, d);
    tree[p] = tree[2 * p] + tree[2 * p + 1];
}

// 区间查询
long long query(int p, int l, int r, int ql, int qr) {
    if (ql <= l && r <= qr) return tree[p];
    int mid = l + (r - l) / 2;
    long long sum = 0;
    if (ql <= mid) sum += query(2 * p, l, mid, ql, qr);
    if (qr > mid)  sum += query(2 * p + 1, mid + 1, r, ql, qr);
    return sum;
}

// 测试：线段树单点修改
int main(void) {
    int n = 8;
    long long init[] = {0, 3, 1, 4, 1, 5, 9, 2, 6};  // 1-indexed
    for (int i = 1; i <= n; i++) a[i] = init[i];

    build(1, 1, n);
    printf("初始数组：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：3 1 4 1 5 9 2 6\n");
    printf("区间[3, 7] 和 = %lld\n", query(1, 1, n, 3, 7));

    update(1, 1, n, 6, 3);  // 位置 6 加上 3 → a[6]=12
    printf("\n位置 6 加 3 后：\n");
    printf("区间[3, 7] 和 = %lld（期望 4+1+5+12+2=24）\n", query(1, 1, n, 3, 7));

    return 0;
}
