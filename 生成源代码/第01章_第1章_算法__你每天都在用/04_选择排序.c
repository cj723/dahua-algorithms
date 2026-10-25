/* 选择排序 */
#include <stdio.h>

void selection_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int minIdx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[minIdx]) {
                minIdx = j;
            }
        }
        /* 注意:这个交换可能跳过同分元素,打乱相对顺序——这就是不稳定的原因 */
        if (minIdx != i) {
            int temp = arr[i];
            arr[i] = arr[minIdx];
            arr[minIdx] = temp;
        }
    }
}

int main(void) {
    int arr[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("排序前: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    selection_sort(arr, n);

    printf("排序后: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    return 0;
}
