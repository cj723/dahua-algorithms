#include <stdio.h>

#define MAXN 100010

int a[MAXN];
long long tree[4 * MAXN];

void build(int p, int l, int r) {
    if (l == r) {
        tree[p] = a[l];
        return;
    }
    int mid = l + (r - l) / 2;  /* 防溢出写法！ */
    build(2 * p, l, mid);
    build(2 * p + 1, mid + 1, r);
    tree[p] = tree[2 * p] + tree[2 * p + 1];
}

void update(int p, int l, int r, int x, long long d) {
    if (l == r) {
        tree[p] += d;
        return;
    }
    int mid = l + (r - l) / 2;
    if (x <= mid)
        update(2 * p, l, mid, x, d);
    else
        update(2 * p + 1, mid + 1, r, x, d);
    tree[p] = tree[2 * p] + tree[2 * p + 1];
}

long long query(int p, int l, int r, int ql, int qr) {
    if (ql <= l && r <= qr) return tree[p];
    int mid = l + (r - l) / 2;
    long long sum = 0;
    if (ql <= mid) sum += query(2 * p, l, mid, ql, qr);
    if (qr > mid) sum += query(2 * p + 1, mid + 1, r, ql, qr);
    return sum;
}

int main(void) {
    // 固定测试数据，便于直接运行观察结果
    int n = 8;
    int init[] = {0, 3, 1, 4, 1, 5, 9, 2, 6};  // 1-indexed
    for (int i = 1; i <= n; i++) a[i] = init[i];

    printf("线段树测试：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：3 1 4 1 5 9 2 6\n");
    build(1, 1, n);

    printf("区间[3, 7] 之和: %lld\n", query(1, 1, n, 3, 7));
    printf("区间[1, 4] 之和: %lld\n", query(1, 1, n, 1, 4));
    update(1, 1, n, 6, 3);
    printf("a[6] 加 3 后，区间[3, 7] 之和: %lld\n", query(1, 1, n, 3, 7));
    return 0;
}
