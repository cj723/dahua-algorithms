#include <stdio.h>

void shell_sort(int arr[], int n) {
    // gap 从 n/2 开始，每轮折半，直到 1
    for (int gap = n / 2; gap > 0; gap /= 2) {
        // 对每个 gap，做一轮"间隔为 gap"的插入排序
        for (int i = gap; i < n; i++) {
            int temp = arr[i];
            int j = i;
            while (j >= gap && arr[j - gap] > temp) {
                arr[j] = arr[j - gap];
                j -= gap;
            }
            arr[j] = temp;
        }
    }
}

// 测试：希尔排序
int main(void) {
    int arr[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("排序前：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    shell_sort(arr, n);

    printf("排序后：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    return 0;
}
