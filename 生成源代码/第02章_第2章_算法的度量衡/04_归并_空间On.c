#include <stdio.h>
#include <stdlib.h>

/* 合并两个有序子数组；成功返回 1，内存分配失败返回 0 */
int merge(int arr[], int left, int mid, int right) {
    int n1 = mid - left + 1;  /* 左半部分的大小 */
    int n2 = right - mid;      /* 右半部分的大小 */
    
    /* 创建临时数组——这就是额外空间！ */
    int *L = (int *)malloc(n1 * sizeof(int));
    int *R = (int *)malloc(n2 * sizeof(int));
    if (L == NULL || R == NULL) {
        free(L);
        free(R);
        return 0;
    }
    
    /* 拷贝数据到临时数组 */
    for (int i = 0; i < n1; i++)
        L[i] = arr[left + i];
    for (int j = 0; j < n2; j++)
        R[j] = arr[mid + 1 + j];
    
    /* 合并回原数组 */
    int i = 0, j = 0, k = left;
    while (i < n1 && j < n2) {
        if (L[i] <= R[j]) {
            arr[k++] = L[i++];
        } else {
            arr[k++] = R[j++];
        }
    }
    
    /* 把剩余的元素也塞进去 */
    while (i < n1) arr[k++] = L[i++];
    while (j < n2) arr[k++] = R[j++];
    
    free(L);
    free(R);
    return 1;
}

/* 归并排序；成功返回 1，失败返回 0 */
int merge_sort(int arr[], int left, int right) {
    if (left < right) {
        int mid = left + (right - left) / 2;
        if (!merge_sort(arr, left, mid)) return 0;       /* 排左半 */
        if (!merge_sort(arr, mid + 1, right)) return 0;  /* 排右半 */
        if (!merge(arr, left, mid, right)) return 0;     /* 合并 */
    }
    return 1;
}

int main(void) {
    int arr[] = {38, 27, 43, 3, 9, 82, 10};
    int n = 7;
    
    if (!merge_sort(arr, 0, n - 1)) {
        fprintf(stderr, "内存分配失败，排序未完成。\n");
        return 1;
    }
    
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
    
    return 0;
}
