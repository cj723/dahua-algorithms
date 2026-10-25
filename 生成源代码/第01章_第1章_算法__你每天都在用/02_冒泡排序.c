/* 冒泡排序 */
#include <stdio.h>

void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - 1 - i; j++) {
            if (arr[j] > arr[j + 1]) {
                /* 交换 */
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
}

int main(void) {
    int arr[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("排序前: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    bubble_sort(arr, n);

    printf("排序后: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    return 0;
}
