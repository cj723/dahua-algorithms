/* 拉斯维加斯算法：随机化选择第 k 小的元素 */
/* 一定会返回正确结果，但运行时间随机 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 交换两个整数 */
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

/* 随机化分区（和快排的分区一样） */
int partition(int arr[], int low, int high) {
    /* 随机选 pivot——拉斯维加斯的关键 */
    /* rand() % N 只适合教学演示，工程中要注意 RAND_MAX、取模偏差和随机数质量 */
    int random_idx = low + rand() % (high - low + 1);
    swap(&arr[random_idx], &arr[high]);

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

/* 随机化选择：找第 k 小的元素（k 从 1 开始） */
/* 这是一个拉斯维加斯算法——结果一定正确，期望 O(n)，最坏仍可能 O(n^2) */
int randomized_select(int arr[], int low, int high, int k) {
    if (low == high) {  /* 只剩一个元素 */
        return arr[low];
    }

    /* 随机分区 */
    int pi = partition(arr, low, high);
    /* pi - low + 1 是 pivot 在当前子数组中的排名 */
    int rank = pi - low + 1;

    if (k == rank) {
        /* pivot 就是第 k 小的元素！找到了！ */
        return arr[pi];
    } else if (k < rank) {
        /* 第 k 小的元素在左边 */
        return randomized_select(arr, low, pi - 1, k);
    } else {
        /* 第 k 小的元素在右边，注意要调整 k 的值 */
        return randomized_select(arr, pi + 1, high, k - rank);
    }
}

int main(void) {
    int arr[] = {7, 10, 4, 3, 20, 15};
    int n = 6;
    int k = 3;  /* 找第 3 小的元素 */

    srand((unsigned int)time(NULL));

    if (k < 1 || k > n) {
        printf("k 不合法\n");
        return 1;
    }

    /* 找第 k 小的元素 */
    int result = randomized_select(arr, 0, n - 1, k);
    printf("第 %d 小的元素是：%d\n", k, result);
    /* 应该输出 7 */

    return 0;
}
