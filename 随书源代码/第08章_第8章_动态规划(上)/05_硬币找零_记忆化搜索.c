#include <stdio.h>

#define MAX_AMOUNT 10000
#define INF 1000000000

int memo[MAX_AMOUNT + 1];

int min_coins_memo(int coins[], int coinCount, int amount) {
    if (amount == 0) return 0;
    if (amount < 0) return INF;
    if (amount > MAX_AMOUNT) return INF;

    if (memo[amount] != -1) {
        return memo[amount];
    }

    int best = INF;
    for (int i = 0; i < coinCount; i++) {
        int sub = min_coins_memo(coins, coinCount, amount - coins[i]);
        if (sub != INF && sub + 1 < best) {
            best = sub + 1;
        }
    }

    memo[amount] = best;
    return best;
}

int main(void) {
    int coins[] = {1, 3, 4};
    int coinCount = sizeof(coins) / sizeof(coins[0]);

    for (int i = 0; i <= MAX_AMOUNT; i++) memo[i] = -1;
    printf("最少硬币数：%d\n", min_coins_memo(coins, coinCount, 6));
    return 0;
}
