#include <stdio.h>

#define MAXN 100010
long long tree[4 * MAXN];
long long a[MAXN];

void build(int p, int l, int r) {
    if (l == r) { tree[p] = a[l]; return; }
    int mid = l + (r - l) / 2;
    build(2 * p, l, mid);
    build(2 * p + 1, mid + 1, r);
    tree[p] = tree[2 * p] + tree[2 * p + 1];
}

// 区间查询：查询 [ql, qr] 的区间和
long long query(int p, int l, int r, int ql, int qr) {
    if (ql <= l && r <= qr) {
        return tree[p];  // 当前区间完全被包含，直接返回
    }
    int mid = l + (r - l) / 2;
    long long sum = 0;
    if (ql <= mid) sum += query(2 * p, l, mid, ql, qr);
    if (qr > mid)  sum += query(2 * p + 1, mid + 1, r, ql, qr);
    return sum;
}

// 测试：线段树区间查询
int main(void) {
    int n = 8;
    long long init[] = {0, 3, 1, 4, 1, 5, 9, 2, 6};  // 1-indexed
    for (int i = 1; i <= n; i++) a[i] = init[i];
    build(1, 1, n);

    printf("数组：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：3 1 4 1 5 9 2 6\n\n");
    printf("区间[3, 7] 和 = %lld（期望 4+1+5+9+2=21）\n", query(1, 1, n, 3, 7));
    printf("区间[1, 4] 和 = %lld（期望 3+1+4+1=9）\n", query(1, 1, n, 1, 4));
    printf("区间[6, 8] 和 = %lld（期望 9+2+6=17）\n", query(1, 1, n, 6, 8));

    return 0;
}
