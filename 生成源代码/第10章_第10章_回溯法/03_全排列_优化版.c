#include <stdio.h>

void swap(int *a, int *b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

void print_array(int arr[], int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

void permute(int arr[], int first, int n) {
    if (first == n) {
        print_array(arr, n);
        return;
    }

    for (int i = first; i < n; i++) {
        swap(&arr[first], &arr[i]);   /* 做选择 */
        permute(arr, first + 1, n);   /* 递归 */
        swap(&arr[first], &arr[i]);   /* 撤销选择 */
    }
}

int main(void) {
    int arr[] = {1, 2, 3};
    int n = sizeof(arr) / sizeof(arr[0]);

    permute(arr, 0, n);
    return 0;
}
