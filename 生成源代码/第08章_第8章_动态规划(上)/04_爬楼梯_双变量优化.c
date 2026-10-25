#include <stdio.h>

int climb_stairs_optimized(int n) {
    if (n <= 0) return 0;
    if (n <= 2) return n;

    int prev2 = 1;  /* f(1) */
    int prev1 = 2;  /* f(2) */
    int cur = 0;

    for (int i = 3; i <= n; i++) {
        cur = prev1 + prev2;
        prev2 = prev1;
        prev1 = cur;
    }

    return prev1;
}

int main(void) {
    printf("爬 10 级台阶有 %d 种走法\n", climb_stairs_optimized(10));
    return 0;
}
