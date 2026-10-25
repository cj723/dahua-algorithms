#include <stdio.h>
#include <limits.h>
#include <string.h>

#define MAX_N 100

long long matrix_chain_order(int p[], int n) {
    if (n <= 0 || n > MAX_N) {
        return -1; /* 输入非法 */
    }
    /* n 个矩阵，维度数组 p 有 n + 1 个元素 */
    /* dp[i][j] 表示第 i 到第 j 个矩阵的最小乘法次数 */
    /* 用 long long 防止维度相乘溢出（1000×1000×1000 就已经是 10 亿级别了） */
    long long dp[MAX_N + 1][MAX_N + 1];

    /* 初始化：单个矩阵不需要乘法 */
    memset(dp, 0, sizeof(dp));

    /* len 是链的长度，从 2 开始（至少两个矩阵才有乘法） */
    for (int len = 2; len <= n; len++) {
        for (int i = 1; i <= n - len + 1; i++) {
            int j = i + len - 1;
            dp[i][j] = LLONG_MAX;

            /* 在 i..j 之间找最优切分点 k */
            for (int k = i; k < j; k++) {
                long long cost = dp[i][k] + dp[k + 1][j]
                               + (long long)p[i - 1] * p[k] * p[j];
                if (cost < dp[i][j]) {
                    dp[i][j] = cost;
                }
            }
        }
    }

    return dp[1][n];
}

int main(void) {
    /* 4 个矩阵：A1（10×100），A2（100×5），A3（5×50），A4（50×1） */
    int p[] = {10, 100, 5, 50, 1};
    int n = 4;

    printf("最少乘法次数：%lld\n", matrix_chain_order(p, n));
    /* 输出 1750（比随便加括号省多了） */

    return 0;
}
