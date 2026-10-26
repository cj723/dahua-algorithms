#include <stdio.h>

int binary_search(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;  /* 防溢出：避免 left + right 先相加超过 int 上限 */
        
        if (arr[mid] == target) {
            return mid;       /* 找到了 */
        } else if (arr[mid] < target) {
            left = mid + 1;   /* 目标在右半边 */
        } else {
            right = mid - 1;  /* 目标在左半边 */
        }
    }
    
    return -1;  /* 没找到 */
}


// 测试：二分查找要求数组有序
int main(void) {
    int arr[] = {2, 5, 8, 12, 16, 23, 38, 45, 56, 67, 78, 89};
    int n = sizeof(arr) / sizeof(arr[0]);

    // 找到的情况
    int targets[] = {8, 45, 89, 2};
    for (int i = 0; i < 4; i++) {
        int pos = binary_search(arr, n, targets[i]);
        printf("查找 %d → 位置 %d\n", targets[i], pos);
    }

    // 找不到的情况
    int pos = binary_search(arr, n, 99);
    printf("查找 99 → 位置 %d（未找到）\n", pos);

    return 0;
}
