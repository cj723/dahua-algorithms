#include <stdio.h>
#include <time.h>

/*
 * 这不是严格性能测试，只是用几个简单循环感受数量级差异。
 * 真正运行时间会受编译器优化、硬件、缓存和实现细节影响。
 */
int main(void) {
    int n = 100000;
    int small_n = 10000;
    clock_t start, end;
    long sum = 0;
    long count = 0;

    start = clock();
    for (int i = 0; i < n; i++) {
        sum += i;
    }
    end = clock();
    printf("O(n) 遍历求和：%ld，耗时：%.6f 秒\n",
           sum, (double)(end - start) / CLOCKS_PER_SEC);

    start = clock();
    for (int i = 1; i <= n; i++) {
        int temp = i;
        while (temp > 0) {
            count++;
            temp /= 2;
        }
    }
    end = clock();
    printf("O(n log n) 粗略模拟：%ld 次操作，耗时：%.6f 秒\n",
           count, (double)(end - start) / CLOCKS_PER_SEC);

    start = clock();
    count = 0;
    for (int i = 0; i < small_n; i++) {
        for (int j = 0; j < small_n; j++) {
            count++;
        }
    }
    end = clock();
    printf("O(n^2) n = %d：%ld 次操作，耗时：%.6f 秒\n",
           small_n, count, (double)(end - start) / CLOCKS_PER_SEC);
    printf("如果 n = 100000，O(n^2) 大约需要 100 亿次操作。\n");

    return 0;
}
