/* 冒泡排序 优化版 */
#include <stdio.h>

void bubble_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int swapped = 0;  /* 标记本轮是否有交换 */
        for (int j = 0; j < n - 1 - i; j++) {
            if (arr[j] > arr[j + 1]) {
                int temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
                swapped = 1;
            }
        }
        if (swapped == 0) break;  /* 本轮无交换，说明数组已有序，可提前结束 */
    }
}

int main(void) {
    /* 测试一：乱序数组 */
    int arr1[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int n1 = sizeof(arr1) / sizeof(arr1[0]);

    printf("[测试一：乱序数组]\n");
    printf("排序前: ");
    for (int i = 0; i < n1; i++) printf("%d ", arr1[i]);
    printf("\n");
    bubble_sort(arr1, n1);
    printf("排序后: ");
    for (int i = 0; i < n1; i++) printf("%d ", arr1[i]);
    printf("\n\n");

    /* 测试二：已经有序的数组——优化版应在第一轮就退出 */
    int arr2[] = {10, 20, 30, 40, 50, 60, 70, 80, 90};
    int n2 = sizeof(arr2) / sizeof(arr2[0]);

    printf("[测试二：已有序数组（优化生效场景）]\n");
    printf("排序前: ");
    for (int i = 0; i < n2; i++) printf("%d ", arr2[i]);
    printf("\n");
    bubble_sort(arr2, n2);
    printf("排序后: ");
    for (int i = 0; i < n2; i++) printf("%d ", arr2[i]);
    printf("\n");

    return 0;
}
