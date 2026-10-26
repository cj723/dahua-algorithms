#include <stdio.h>

/* 斐波那契查找 */
/* 在有序数组 arr[0..n-1] 中查找 target */
/* 返回下标，找不到返回 -1 */
int fibonacci_search(int arr[], int n, int target) {
    if (n <= 0) return -1;

    /* 第 1 步：找到满足 F[k] >= n + 1 的最小 k（即扩展长度 F[k] - 1 >= n） */
    int fib2 = 0;   /* F[k-2] */
    int fib1 = 1;   /* F[k-1] */
    int fibK = 1;   /* F[k] */
    
    while (fibK < n + 1) {
        fib2 = fib1;
        fib1 = fibK;
        fibK = fib1 + fib2;
        /* 当 n 很大时（比如 n > 1000000），fibK 可能溢出 int 范围。
           实际工程中应使用 long long 或提前计算 fib 数列上限。*/
    }
    
    /* 第 2 步：概念上将数组扩展到 F[k] - 1 的长度 */
    /* 扩展部分用原数组最后一个元素填充 */
    
    int left = 0;
    
    while (fibK > 1) {
        /* 分割点：left + fib2 - 1，但不超过 n-1 */
        int i = left + fib2 - 1;
        if (i > n - 1) {
            i = n - 1;
        }
        
        if (arr[i] < target) {
            /* 目标在右半段：区间长度从 F[k] - 1 缩小到 F[k - 1] - 1 */
            /* 往右走——斐波那契值下移 1 级 */
            left = i + 1;
            fibK = fib1;
            fib1 = fib2;
            fib2 = fibK - fib1;
        } else if (arr[i] > target) {
            /* 目标在左半段：区间长度从 F[k] - 1 缩小到 F[k - 2] - 1 */
            /* 往左走——斐波那契值下移 2 级 */
            fibK = fib2;
            fib1 = fib1 - fib2;
            fib2 = fibK - fib1;
        } else {
            /* 找到了。i 已经被限制在真实数组范围内 */
            return i;
        }
    }
    
    /* fibK == 1 时还剩一个元素要检查 */
    if (left < n && arr[left] == target) {
        return left;
    }
    
    return -1;  /* 没找到 */
}

int main(void) {
    int arr[] = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19};
    int n = sizeof(arr) / sizeof(arr[0]);
    
    int target = 13;
    int result = fibonacci_search(arr, n, target);
    
    if (result != -1) {
        printf("找到 %d，位置：%d\n", target, result);
    } else {
        printf("未找到 %d\n", target);
    }
    
    return 0;
}
