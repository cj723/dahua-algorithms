#include <stdio.h>

#define INF 1000000000
#define MAX_AMOUNT 10000

int coin_change(int coins[], int coinCount, int amount) {
    if (amount < 0 || amount > MAX_AMOUNT) {
        return -1;  /* 防止 amount 超出 dp 数组范围 */
    }

    int dp[MAX_AMOUNT + 1];

    for (int i = 0; i <= amount; i++) {
        dp[i] = INF;
    }
    dp[0] = 0;

    for (int i = 1; i <= amount; i++) {
        for (int j = 0; j < coinCount; j++) {
            int coin = coins[j];
            if (i >= coin && dp[i - coin] != INF) {
                if (dp[i - coin] + 1 < dp[i]) {
                    dp[i] = dp[i - coin] + 1;
                }
            }
        }
    }

    return dp[amount] == INF ? -1 : dp[amount];
}

int main(void) {
    int coins[] = {1, 2, 5};
    int amount = 11;
    int coinCount = sizeof(coins) / sizeof(coins[0]);

    printf("最少硬币数：%d\n", coin_change(coins, coinCount, amount));
    return 0;
}
