/* 顺序查找 */
#include <stdio.h>

/* 顺序查找：在 arr[0..n-1] 里找 target，返回下标；找不到返回 -1 */
int linear_search(int arr[], int n, int target) {
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) {
            return i;  /* 找到了，返回下标 */
        }
    }
    return -1;  /* 没找到 */
}

int main(void) {
    int arr[] = {50, 10, 90, 30, 70, 40, 80, 60, 20};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("数组内容：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n\n");

    /* 测试一：找一个存在的值 */
    int target1 = 70;
    int idx1 = linear_search(arr, n, target1);
    if (idx1 >= 0)
        printf("找 %d：在下标 %d 处命中\n", target1, idx1);
    else
        printf("找 %d：没找到\n", target1);

    /* 测试二：找一个不存在的值 */
    int target2 = 99;
    int idx2 = linear_search(arr, n, target2);
    if (idx2 >= 0)
        printf("找 %d：在下标 %d 处命中\n", target2, idx2);
    else
        printf("找 %d：没找到\n", target2);

    return 0;
}
