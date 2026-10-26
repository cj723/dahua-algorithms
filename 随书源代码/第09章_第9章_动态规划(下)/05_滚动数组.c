#include <stdio.h>

#define MAX(a, b) ((a) > (b) ? (a) : (b))

/* 原始版本：O(n × W) 空间 */
int knapsack_2d(int wt[], int val[], int n, int W) {
    int dp[n + 1][W + 1];

    for (int i = 0; i <= n; i++)
        for (int w = 0; w <= W; w++)
            dp[i][w] = 0;

    for (int i = 1; i <= n; i++) {
        for (int w = 1; w <= W; w++) {
            if (w >= wt[i - 1]) {
                dp[i][w] = MAX(dp[i - 1][w], val[i - 1] + dp[i - 1][w - wt[i - 1]]);
            } else {
                dp[i][w] = dp[i - 1][w];
            }
        }
    }
    return dp[n][W];
}

/* 第一层优化：只保留上一行和当前行 */
int knapsack_rolling(int wt[], int val[], int n, int W) {
    int dp[2][W + 1];

    for (int row = 0; row < 2; row++) {
        for (int w = 0; w <= W; w++) {
            dp[row][w] = 0;
        }
    }

    for (int i = 1; i <= n; i++) {
        int cur = i % 2;
        int pre = (i - 1) % 2;

        for (int w = 0; w <= W; w++) {
            dp[cur][w] = dp[pre][w];
            if (w >= wt[i - 1]) {
                int choose = dp[pre][w - wt[i - 1]] + val[i - 1];
                if (choose > dp[cur][w]) {
                    dp[cur][w] = choose;
                }
            }
        }
    }

    return dp[n % 2][W];
}

/* 第二层优化：压成一维数组，0-1 背包必须倒序遍历 */
int knapsack_1d(int wt[], int val[], int n, int W) {
    int dp[W + 1];
    for (int w = 0; w <= W; w++) dp[w] = 0;

    for (int i = 0; i < n; i++) {
        for (int w = W; w >= wt[i]; w--) {
            dp[w] = MAX(dp[w], val[i] + dp[w - wt[i]]);
        }
    }
    return dp[W];
}

int main(void) {
    int wt[]  = {1, 4, 3, 1};
    int val[] = {1500, 3000, 2000, 2000};
    int n = 4, W = 4;

    printf("二维 DP（O(nW) 空间）：最大价值 = %d\n",
           knapsack_2d(wt, val, n, W));
    printf("两行滚动（O(W) 空间）：最大价值 = %d\n",
           knapsack_rolling(wt, val, n, W));
    printf("一维压缩（O(W) 空间）：最大价值 = %d\n",
           knapsack_1d(wt, val, n, W));

    return 0;
}
