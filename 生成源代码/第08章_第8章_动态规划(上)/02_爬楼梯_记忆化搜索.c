#include <stdio.h>
#include <string.h>

#define MAXN 1000

int memo[MAXN + 1];

/* 记忆化搜索：先问大问题，遇到小问题就递归求，求完记下来 */
int climb_stairs_memo(int n) {
    if (n <= 0) return 0;
    if (n > MAXN) return -1;
    if (n <= 2) return n;

    if (memo[n] != -1) {
        return memo[n];  /* 算过了，直接拿来用 */
    }

    memo[n] = climb_stairs_memo(n - 1) + climb_stairs_memo(n - 2);
    return memo[n];
}

int main(void) {
    memset(memo, -1, sizeof(memo));
    printf("爬 40 级台阶有 %d 种走法\n", climb_stairs_memo(40));
    return 0;
}
