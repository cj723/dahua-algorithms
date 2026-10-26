#include <stdio.h>

/* 交换两个整数 */
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

/* 分区函数：选最后一个元素为基准，返回基准值的最终位置 */
int partition(int arr[], int low, int high) {
    int pivot = arr[high];    /* 基准值选最后一个元素 */
    int i = low - 1;          /* i 指向“小于基准值区域”的末尾 */

    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {  /* 当前元素比基准值小 */
            i++;
            swap(&arr[i], &arr[j]);  /* 把它扔到“小区”里 */
        }
    }

    swap(&arr[i + 1], &arr[high]);  /* 把基准值放到正确位置 */
    return i + 1;                    /* 返回基准值的位置 */
}

/* 快速排序主函数 */
void quick_sort(int arr[], int low, int high) {
    if (low < high) {
        /* 分区，拿到基准值的位置 */
        int pi = partition(arr, low, high);

        /* 递归排序基准值左边的部分 */
        quick_sort(arr, low, pi - 1);

        /* 递归排序基准值右边的部分 */
        quick_sort(arr, pi + 1, high);
    }
}

/* 测试 */
int main(void) {
    int arr[] = {10, 5, 13, 3, 8, 15, 6};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("排序前：");
    for (int i = 0; i < n; i++)
        printf(" %d", arr[i]);
    printf("\n");

    quick_sort(arr, 0, n - 1);

    printf("排序后：");
    for (int i = 0; i < n; i++)
        printf(" %d", arr[i]);
    printf("\n");

    return 0;
}
