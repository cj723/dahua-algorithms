#include <stdio.h>

/* 打印数组，方便观察每个样例的排序结果 */
void print_array(const int arr[], int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

/* 插入排序：左侧保持有序，每次把新元素插入正确位置 */
void insertion_sort(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;

        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }

        arr[j + 1] = key;
    }
}

/* 运行一个样例，避免 main 里重复写打印逻辑 */
void run_case(const char *name, int arr[], int n) {
    printf("=== %s ===\n", name);
    printf("排序前: ");
    print_array(arr, n);

    insertion_sort(arr, n);

    printf("排序后: ");
    print_array(arr, n);
    printf("\n");
}

int main(void) {
    int normal[] = {5, 2, 4, 6, 1, 3};
    int nearlySorted[] = {1, 2, 3, 5, 4, 6};
    int reversed[] = {6, 5, 4, 3, 2, 1};

    run_case("普通无序数组", normal, 6);
    run_case("接近有序数组", nearlySorted, 6);
    run_case("完全逆序数组", reversed, 6);

    return 0;
}
