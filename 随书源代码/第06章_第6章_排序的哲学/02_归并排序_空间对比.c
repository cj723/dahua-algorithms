#include <stdio.h>
#include <stdlib.h>

/* 归并排序：需要额外 O(n) 空间 */
int merge(int arr[], int left, int mid, int right) {
    int n1 = mid - left + 1;
    int n2 = right - mid;

    /* 看！这里申请了两个临时数组：这就是“搬家”的代价 */
    int *L = (int *)malloc(n1 * sizeof(int));
    int *R = (int *)malloc(n2 * sizeof(int));
    if (!L || !R) {
        free(L);
        free(R);
        return 0;
    }

    for (int i = 0; i < n1; i++) L[i] = arr[left + i];
    for (int j = 0; j < n2; j++) R[j] = arr[mid + 1 + j];

    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) arr[k++] = L[i++];
        else arr[k++] = R[j++];
    }
    while (i < n1) arr[k++] = L[i++];
    while (j < n2) arr[k++] = R[j++];

    free(L);
    free(R);
    return 1;
}

int merge_sort(int arr[], int left, int right) {
    if (left < right) {
        int mid = left + (right - left) / 2;
        if (!merge_sort(arr, left, mid)) return 0;
        if (!merge_sort(arr, mid + 1, right)) return 0;
        if (!merge(arr, left, mid, right)) return 0;
    }
    return 1;
}


// 测试：归并排序需要 O(n) 额外空间（对比快速排序的原地操作）
int main(void) {
    int arr[] = {38, 27, 43, 3, 9, 82, 10};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("归并排序——需要额外 O(n) 空间：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    printf("排序前：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    if (!merge_sort(arr, 0, n - 1)) {
        printf("排序失败：内存不足。\n");
        return 1;
    }

    printf("排序后：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    printf("说明：merge() 中 malloc 了 L[] 和 R[] 两个临时数组，这就是 O(n) 额外空间的来源\n");
    return 0;
}
