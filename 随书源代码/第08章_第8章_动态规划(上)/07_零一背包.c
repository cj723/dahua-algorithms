#include <stdio.h>

#define MAX_N 100
#define MAX_W 1000

int max(int a, int b) {
    return a > b ? a : b;
}

/* 0-1 背包：每件物品最多选一次 */
int knapsack01(int wt[], int val[], int n, int W) {
    if (n < 0 || n > MAX_N || W < 0 || W > MAX_W) {
        return -1;  /* 防止 n 或 W 超出 dp 数组范围 */
    }

    int dp[MAX_N + 1][MAX_W + 1];
    
    /* 初始化：前 0 件物品，或者容量为 0，价值都是 0 */
    for (int i = 0; i <= n; i++) {
        for (int w = 0; w <= W; w++) {
            dp[i][w] = 0;
        }
    }
    
    for (int i = 1; i <= n; i++) {
        for (int w = 1; w <= W; w++) {
            if (wt[i - 1] <= w) {
                dp[i][w] = max(
                    dp[i - 1][w],
                    val[i - 1] + dp[i - 1][w - wt[i - 1]]
                );
            } else {
                dp[i][w] = dp[i - 1][w];
            }
        }
    }
    
    return dp[n][W];
}

int main(void) {
    int wt[]  = {1, 4, 3, 1};
    int val[] = {1500, 3000, 2000, 2000};
    int n = 4;
    int W = 4;
    
    printf("最大价值：%d\n", knapsack01(wt, val, n, W));
    return 0;
}
