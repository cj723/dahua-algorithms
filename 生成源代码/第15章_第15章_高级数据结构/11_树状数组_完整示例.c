#include <stdio.h>

#define MAXN 500010

int n;
long long c[MAXN], a[MAXN];

int lowbit(int x) { return x & (-x); }

void update(int x, long long v) {
    if (x <= 0) {
        printf("错误：树状数组下标必须从 1 开始\n");
        return;
    }
    for (int i = x; i <= n; i += lowbit(i))
        c[i] += v;
}

long long query(int x) {
    long long s = 0;
    for (int i = x; i > 0; i -= lowbit(i))
        s += c[i];
    return s;
}

int main(void) {
    // 固定测试数据，便于直接运行观察结果
    n = 8;
    long long init[] = {0, 1, 2, 3, 4, 5, 6, 7, 8};  // 1-indexed
    for (int i = 1; i <= n; i++) {
        a[i] = init[i];
        update(i, init[i]);
    }

    printf("树状数组测试：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：1 2 3 4 5 6 7 8\n");

    printf("前缀和 sum(7): %lld\n", query(7));
    printf("区间和 [3, 7]: %lld\n", query(7) - query(2));
    update(5, 10);  // a[5] 从 5 加到 15，影响 c[5]、c[6]、c[8]
    a[5] += 10;
    printf("a[5] 加 10 后，前缀和 sum(7): %lld\n", query(7));
    printf("a[5] 加 10 后，区间和 [3, 7]: %lld\n", query(7) - query(2));
    return 0;
}
