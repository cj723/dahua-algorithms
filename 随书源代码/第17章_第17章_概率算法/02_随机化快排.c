/* 随机化快速排序 */
/* 类比：抽签——随机选一个基准值，避免极端情况 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 交换两个整数 */
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

/* 随机化分区函数 */
/* 返回 pivot 最终的位置 */
int randomized_partition(int arr[], int low, int high) {
    /* 关键：随机选择一个 pivot，而不是固定选第一个或最后一个 */
    /* rand() % N 只适合教学演示，工程中要注意 RAND_MAX、取模偏差和随机数质量 */
    int random_index = low + rand() % (high - low + 1);
    /* 把随机选的元素换到最后，方便后面的分区操作 */
    swap(&arr[random_index], &arr[high]);

    int pivot = arr[high];  /* 以最后一个元素为 pivot */
    int i = low - 1;        /* i 指向“小于 pivot 区域”的末尾 */
    /* 遍历数组，把小于 pivot 的元素都交换到左边 */
    for (int j = low; j < high; j++) {
        if (arr[j] < pivot) {   /* 当前元素小于 pivot */
            i++;                /* 扩大“小元素区域” */
            swap(&arr[i], &arr[j]);  /* 交换到左边 */
        }
    }

    /* 把 pivot 放到正确的位置 */
    swap(&arr[i + 1], &arr[high]);
    return i + 1;  /* 返回 pivot 的位置 */
}

/* 随机化快速排序 */
void randomized_quicksort(int arr[], int low, int high) {
    if (low < high) {  /* 递归终止条件：子数组长度为 1 */
        /* 分区：找到 pivot 的正确位置 */
        int pi = randomized_partition(arr, low, high);
        /* 递归排序左半部分 */
        randomized_quicksort(arr, low, pi - 1);
        /* 递归排序右半部分 */
        randomized_quicksort(arr, pi + 1, high);
    }
}

/* 测试代码 */
int main(void) {
    int arr[] = {5, 3, 8, 1, 9, 2, 7, 4, 6};
    int n = 9;

    /* 初始化随机数种子 */
    srand((unsigned int)time(NULL));

    printf("排序前: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    randomized_quicksort(arr, 0, n - 1);

    printf("排序后: ");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n");

    return 0;
}
