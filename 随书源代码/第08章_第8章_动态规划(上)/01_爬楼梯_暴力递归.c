#include <stdio.h>

/* 暴力递归：爬 n 级台阶的走法数 */
int climb_stairs(int n) {
    if (n <= 0) return 0;
    if (n <= 2) return n;
    return climb_stairs(n - 1) + climb_stairs(n - 2);
}

int main(void) {
    printf("爬 6 级台阶有 %d 种走法\n", climb_stairs(6));
    printf("爬 10 级台阶有 %d 种走法\n", climb_stairs(10));
    return 0;
}
