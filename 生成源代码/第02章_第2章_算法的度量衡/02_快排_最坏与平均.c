#include <stdio.h>

/* 交换两个数 */
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

/* 分区函数：选最后一个元素作为基准，小的放左边，大的放右边 */
int partition(int arr[], int low, int high) {
    int pivot = arr[high];  /* 基准值 */
    int i = low - 1;        /* "小元素区"的边界 */
    
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {
            i++;
            swap(&arr[i], &arr[j]);
        }
    }
    swap(&arr[i + 1], &arr[high]);
    return i + 1;
}

/* 快速排序 */
void quick_sort(int arr[], int low, int high) {
    if (low < high) {
        int pi = partition(arr, low, high);
        quick_sort(arr, low, pi - 1);   /* 排左边 */
        quick_sort(arr, pi + 1, high);  /* 排右边 */
    }
}

void print_array(int arr[], int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

int main(void) {
    int arr[] = {10, 7, 8, 9, 1, 5};
    int n = 6;
    
    printf("排序前：");
    print_array(arr, n);
    
    quick_sort(arr, 0, n - 1);
    
    printf("排序后：");
    print_array(arr, n);
    
    return 0;
}
