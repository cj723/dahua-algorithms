#include <stdio.h>

/* 顺序查找：从头到尾一个一个比 */
/* arr：数组，n：数组长度，target：要找的目标 */
int sequential_search(int arr[], int n, int target) {
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) {
            return i;  /* 找到了，返回下标 */
        }
    }
    return -1;  /* 没找到 */
}

int main(void) {
    int arr[] = {3, 7, 1, 9, 5, 2, 8, 4, 6, 0};
    int n = 10;
    
    /* 最好情况：target = 3，第一个就命中 */
    printf("找 3：第 %d 步找到\n", sequential_search(arr, n, 3) + 1);
    
    /* 最坏情况：target = 0，最后一个才找到 */
    printf("找 0：第 %d 步找到\n", sequential_search(arr, n, 0) + 1);
    
    /* 平均情况：假设目标等概率出现，
       平均步数为 (1 + 2 + ... + 10) / 10 = 5.5 步，
       因此在一般情况下仍属于 O(n) */
    
    return 0;
}
