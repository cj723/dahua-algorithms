#include <stdio.h>
#include <stdlib.h>

/* 合并两个有序子数组 arr[left..mid] 和 arr[mid + 1..right] */
void merge(int arr[], int left, int mid, int right) {
    int n1 = mid - left + 1;   /* 左半部分的长度 */
    int n2 = right - mid;       /* 右半部分的长度 */

    /* 在堆上动态分配临时数组 */
    int *L = (int *)malloc(n1 * sizeof(int));
    int *R = (int *)malloc(n2 * sizeof(int));

    if (L == NULL || R == NULL) {
        free(L);
        free(R);
        fprintf(stderr, "内存分配失败\n");
        exit(EXIT_FAILURE);
    }

    /* 把数据拷贝到临时数组 */
    for (int i = 0; i < n1; i++)
        L[i] = arr[left + i];
    for (int j = 0; j < n2; j++)
        R[j] = arr[mid + 1 + j];

    /* 合并临时数组回 arr[left..right] */
    int i = 0, j = 0, k = left;

    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {    /* 左边的更小，取左边的 */
            arr[k] = L[i];
            i++;
        } else {                /* 右边的更小，取右边的 */
            arr[k] = R[j];
            j++;
        }
        k++;
    }

    /* 把左边剩余的元素全搬过来 */
    while (i < n1) {
        arr[k] = L[i];
        i++; k++;
    }

    /* 把右边剩余的元素全搬过来 */
    while (j < n2) {
        arr[k] = R[j];
        j++; k++;
    }

    /* 释放临时数组（别忘了！） */
    free(L);
    free(R);
}

/* 归并排序主函数 */
void merge_sort(int arr[], int left, int right) {
    if (left < right) {             /* 终止条件：只剩一个元素时 left == right */
        int mid = left + (right - left) / 2;  /* 防溢出的中点写法 */

        merge_sort(arr, left, mid);       /* 递归排序左半部分 */
        merge_sort(arr, mid + 1, right);  /* 递归排序右半部分 */
        merge(arr, left, mid, right);     /* 合并两个有序子数组 */
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

    merge_sort(arr, 0, n - 1);

    printf("排序后：");
    for (int i = 0; i < n; i++)
        printf(" %d", arr[i]);
    printf("\n");

    return 0;
}
