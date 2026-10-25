#include <stdio.h>
#include <stdlib.h>

/* 获取数组中的最大值 */
int get_max(int arr[], int n) {
    int max = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] > max) {
            max = arr[i];
        }
    }
    return max;
}

/*
 * 按指定位（exp）进行稳定的计数排序
 * exp = 1 表示个位，10 表示十位，100 表示百位……
 */
void counting_sort_by_digit(int arr[], int n, long long exp) {
    int *result = (int *)malloc(n * sizeof(int));
    int count[10] = {0};  /* 十进制，每位只有 0～9 */
    if (!result) return;
    
    /* 唱票：统计当前位每个数字出现的次数 */
    for (int i = 0; i < n; i++) {
        int digit = (arr[i] / exp) % 10;
        count[digit]++;
    }
    
    /* 累加 */
    for (int i = 1; i < 10; i++) {
        count[i] += count[i - 1];
    }
    
    /* 从后往前，稳定地放置元素 */
    for (int i = n - 1; i >= 0; i--) {
        int digit = (arr[i] / exp) % 10;
        result[count[digit] - 1] = arr[i];
        count[digit]--;
    }
    
    /* 拷回原数组 */
    for (int i = 0; i < n; i++) {
        arr[i] = result[i];
    }
    
    free(result);
}

/*
 * 基数排序（LSD: Least Significant Digit First）
 * 从最低位开始，逐位排序
 */
void radix_sort(int arr[], int n) {
    if (n <= 0) return;

    int max = get_max(arr, n);
    
    /* 对每一位进行计数排序 */
    /* exp: 1, 10, 100, 1000, ... */
    for (long long exp = 1; max / exp > 0; exp *= 10) {
        counting_sort_by_digit(arr, n, exp);
        
        /* 打印每轮的结果，方便理解 */
        printf("按位 %lld 排序后：", exp);
        for (int i = 0; i < n; i++) {
            printf("%d ", arr[i]);
        }
        printf("\n");
    }
}

int main(void) {
    int arr[] = {170, 45, 75, 90, 802, 24, 2, 66};
    int n = sizeof(arr) / sizeof(arr[0]);
    
    printf("原始数组：");
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n\n");
    
    radix_sort(arr, n);
    
    printf("\n最终结果：");
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
    
    return 0;
}
