#include <stdio.h>

#define INSERTION_THRESHOLD 8

static void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

static void print_array(const int arr[], int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

/* 小数组用插入排序，常数开销更小 */
static void insertion_sort_range(int arr[], int low, int high) {
    for (int i = low + 1; i <= high; i++) {
        int key = arr[i];
        int j = i - 1;

        while (j >= low && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }

        arr[j + 1] = key;
    }
}

static int median_of_three(int arr[], int low, int high) {
    int mid = low + (high - low) / 2;

    if (arr[mid] < arr[low]) swap(&arr[mid], &arr[low]);
    if (arr[high] < arr[low]) swap(&arr[high], &arr[low]);
    if (arr[high] < arr[mid]) swap(&arr[high], &arr[mid]);

    return mid;  /* 此时 arr[mid] 是三者中的中间值 */
}

static int partition(int arr[], int low, int high) {
    int pivotIndex = median_of_three(arr, low, high);
    swap(&arr[pivotIndex], &arr[high]);

    int pivot = arr[high];
    int i = low - 1;

    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {
            i++;
            swap(&arr[i], &arr[j]);
        }
    }

    swap(&arr[i + 1], &arr[high]);
    return i + 1;
}

static void heapify_range(int arr[], int low, int heapSize, int root) {
    int largest = root;
    int left = 2 * root + 1;
    int right = 2 * root + 2;

    if (left < heapSize && arr[low + left] > arr[low + largest]) {
        largest = left;
    }
    if (right < heapSize && arr[low + right] > arr[low + largest]) {
        largest = right;
    }

    if (largest != root) {
        swap(&arr[low + root], &arr[low + largest]);
        heapify_range(arr, low, heapSize, largest);
    }
}

/* 递归太深时切换堆排序，避免快排退化到 O(n^2) */
static void heap_sort_range(int arr[], int low, int high) {
    int heapSize = high - low + 1;

    for (int i = heapSize / 2 - 1; i >= 0; i--) {
        heapify_range(arr, low, heapSize, i);
    }

    for (int end = heapSize - 1; end > 0; end--) {
        swap(&arr[low], &arr[low + end]);
        heapify_range(arr, low, end, 0);
    }
}

static int floor_log2(int n) {
    int result = 0;

    while (n > 1) {
        n >>= 1;
        result++;
    }

    return result;
}

static void quick_sort_engine(int arr[], int low, int high, int depthLimit) {
    while (high - low + 1 > INSERTION_THRESHOLD) {
        if (depthLimit == 0) {
            heap_sort_range(arr, low, high);  /* 兜底：避免快排退化 */
            return;
        }
        depthLimit--;

        int pivotPos = partition(arr, low, high);
        int leftSize = pivotPos - low;
        int rightSize = high - pivotPos;

        /* 只递归较小的一边，较大的一边继续 while 循环 */
        if (leftSize < rightSize) {
            quick_sort_engine(arr, low, pivotPos - 1, depthLimit);
            low = pivotPos + 1;
        } else {
            quick_sort_engine(arr, pivotPos + 1, high, depthLimit);
            high = pivotPos - 1;
        }
    }

    insertion_sort_range(arr, low, high);  /* 小数组收尾 */
}

void quick_sort_optimized(int arr[], int n) {
    if (n <= 1) return;

    int depthLimit = 2 * floor_log2(n);
    quick_sort_engine(arr, 0, n - 1, depthLimit);
}

static void run_case(const char *name, int arr[], int n) {
    printf("=== %s ===\n", name);
    printf("排序前: ");
    print_array(arr, n);

    quick_sort_optimized(arr, n);

    printf("排序后: ");
    print_array(arr, n);
    printf("\n");
}

int main(void) {
    int normal[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int sorted[] = {10, 20, 30, 40, 50, 60, 70, 80, 90};
    int reversed[] = {90, 80, 70, 60, 50, 40, 30, 20, 10};
    int repeated[] = {30, 10, 30, 20, 10, 40, 30, 20, 50};

    run_case("普通无序数组", normal, 9);
    run_case("已经有序数组", sorted, 9);
    run_case("完全逆序数组", reversed, 9);
    run_case("包含重复元素", repeated, 9);

    return 0;
}
