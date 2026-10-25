#include <stdio.h>
#include <stdlib.h>

static int min_value(int a, int b) {
    return a < b ? a : b;
}

int coin_change(int *coins, int coinsSize, int amount) {
    if (amount < 0) return -1;
    if (amount == 0) return 0;
    if (coinsSize <= 0) return -1;

    int *dp = (int *)malloc((amount + 1) * sizeof(int));
    if (dp == NULL) return -1;

    /* amount + 1 是一个安全的“无穷大” */
    for (int i = 0; i <= amount; i++) {
        dp[i] = amount + 1;
    }
    dp[0] = 0;

    for (int j = 0; j < coinsSize; j++) {
        int coin = coins[j];
        if (coin <= 0) continue;  /* 防御非法面额 */

        for (int i = coin; i <= amount; i++) {
            dp[i] = min_value(dp[i], dp[i - coin] + 1);
        }
    }

    int result = dp[amount];
    free(dp);

    return result > amount ? -1 : result;
}

int main(void) {
    int coins1[] = {1, 2, 5};
    int amount1 = 11;
    printf("硬币[1,2,5] 凑 %d 元：%d（期望 3）\n",
           amount1, coin_change(coins1, 3, amount1));

    int coins2[] = {2};
    int amount2 = 3;
    printf("硬币[2] 凑 %d 元：%d（期望 -1）\n",
           amount2, coin_change(coins2, 1, amount2));

    int coins3[] = {1};
    int amount3 = 0;
    printf("硬币[1] 凑 %d 元：%d（期望 0）\n",
           amount3, coin_change(coins3, 1, amount3));

    return 0;
}
