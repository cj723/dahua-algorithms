#include <stdio.h>

void heapify(int arr[], int n, int i) {
    int largest = i;
    int left = 2 * i + 1;
    int right = 2 * i + 2;

    if (left < n && arr[left] > arr[largest])
        largest = left;
    if (right < n && arr[right] > arr[largest])
        largest = right;

    if (largest != i) {
        int temp = arr[i];
        arr[i] = arr[largest];
        arr[largest] = temp;
        heapify(arr, n, largest);
    }
}

void heap_sort(int arr[], int n) {
    // 建堆：从最后一个非叶节点开始
    for (int i = n / 2 - 1; i >= 0; i--)
        heapify(arr, n, i);

    // 一个个取出堆顶
    for (int i = n - 1; i > 0; i--) {
        int temp = arr[0];
        arr[0] = arr[i];
        arr[i] = temp;
        heapify(arr, i, 0);
    }
}


/* ===== 自动生成的测试入口 ===== */
#define N 9
int main(void) {
    int d[N] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int i;

    printf("=== heapify ===\n");
    {
        int arr[N];
        for (i = 0; i < N; i++) arr[i] = d[i];
        printf("调整前: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
        heapify(arr, N, 0);
        printf("调整后（仅修复根节点的堆性质）: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
    }

    printf("=== heap_sort ===\n");
    {
        int arr[N];
        for (i = 0; i < N; i++) arr[i] = d[i];
        printf("排序前: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
        heap_sort(arr, N);
        printf("排序后: ");
        for (i = 0; i < N; i++) printf("%d ", arr[i]);
        printf("\n");
    }

    return 0;
}
