/* 循环累加 */
#include <stdio.h>

/* 循环累加法：O(n)。n 较大时结果可能超过 int 范围，因此用 long long 保存和。 */
long long sum_loop(int n) {
    long long sum = 0;
    for (int i = 1; i <= n; i++) {
        sum += i;
    }
    return sum;
}

int main(void) {
    int test_values[] = {10, 100, 10000, 1000000};
    int count = sizeof(test_values) / sizeof(test_values[0]);

    printf("方法一：循环累加（O(n)）\n");
    for (int k = 0; k < count; k++) {
        int n = test_values[k];
        printf("  1 + 2 + ... + %-7d = %lld\n", n, sum_loop(n));
    }
    return 0;
}
