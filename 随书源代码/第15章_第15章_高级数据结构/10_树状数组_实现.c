#include <stdio.h>

#define MAXN 500010

int n;
long long c[MAXN];

int lowbit(int x) {
    return x & (-x);
}

// 单点修改：把位置 x 的值加上 v
void update(int x, long long v) {
    if (x <= 0) {
        printf("错误：树状数组下标必须从 1 开始\n");
        return;
    }
    for (int i = x; i <= n; i += lowbit(i)) {
        c[i] += v;
    }
}

// 前缀和查询：求 a[1] + a[2] + ... + a[x]
long long query(int x) {
    long long sum = 0;
    for (int i = x; i > 0; i -= lowbit(i)) {
        sum += c[i];
    }
    return sum;
}

// 区间和查询：求 a[l] + ... + a[r]
long long range_query(int l, int r) {
    return query(r) - query(l - 1);
}


// 测试：树状数组（Fenwick Tree / BIT）
int main(void) {
    n = 8;
    // 初始化：在位置 i 上加上值 a[i]
    long long init[] = {0, 1, 2, 3, 4, 5, 6, 7, 8};  // 1-indexed
    for (int i = 1; i <= n; i++) update(i, init[i]);

    printf("数组：\n");
    printf("下标：1 2 3 4 5 6 7 8\n");
    printf("数值：1 2 3 4 5 6 7 8\n\n");
    printf("前缀和 query(7) = %lld（期望 1+2+3+4+5+6+7=28）\n", query(7));
    printf("前缀和 query(8) = %lld（期望 36）\n", query(8));
    printf("区间和 [3, 7] = %lld（期望 3+4+5+6+7=25）\n", range_query(3, 7));

    printf("\nupdate(5, 10) → a[5] 从 5 变成 15\n");
    update(5, 10);
    printf("前缀和 query(7) = %lld（期望 38）\n", query(7));
    printf("区间和 [3, 7] = %lld（期望 35）\n", range_query(3, 7));

    return 0;
}
