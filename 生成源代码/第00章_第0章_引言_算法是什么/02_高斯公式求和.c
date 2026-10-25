/* 高斯公式求和 */
#include <stdio.h>

/* 数学公式法：O(1)。先转成 long long，避免 n * (n + 1) 在 int 中溢出。 */
long long sum_formula(int n) {
    return (long long)n * (n + 1) / 2;
}

int main(void) {
    int test_values[] = {10, 100, 10000, 1000000};
    int count = sizeof(test_values) / sizeof(test_values[0]);

    printf("方法二：数学公式（O(1)）\n");
    for (int k = 0; k < count; k++) {
        int n = test_values[k];
        printf("  1 + 2 + ... + %-7d = %lld\n", n, sum_formula(n));
    }
    return 0;
}
