#include <stdio.h>

#define MAXN 1000

int climb_stairs_dp(int n) {
    if (n <= 0) return 0;
    if (n > MAXN) return -1;
    if (n <= 2) return n;

    int dp[MAXN + 1];
    dp[1] = 1;
    dp[2] = 2;

    for (int i = 3; i <= n; i++) {
        dp[i] = dp[i - 1] + dp[i - 2];
    }

    return dp[n];
}

int main(void) {
    printf("爬 10 级台阶有 %d 种走法\n", climb_stairs_dp(10));
    return 0;
}
