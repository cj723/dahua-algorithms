#include <stdio.h>

int search_rotated(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;
        
        if (arr[mid] == target) {
            return mid;
        }
        
        /* 判断左半边是否有序 */
        if (arr[left] <= arr[mid]) {
            /* 左半边有序，看看 target 是不是在左半边的范围内 */
            if (arr[left] <= target && target < arr[mid]) {
                right = mid - 1;  /* 在左半边 */
            } else {
                left = mid + 1;   /* 在右半边 */
            }
        } else {
            /* 右半边有序，看看 target 是不是在右半边的范围内 */
            if (arr[mid] < target && target <= arr[right]) {
                left = mid + 1;   /* 在右半边 */
            } else {
                right = mid - 1;  /* 在左半边 */
            }
        }
    }
    
    return -1;
}


// 测试：旋转数组搜索（如 {4,5,6,7,0,1,2} 是 {0,1,2,4,5,6,7} 旋转而来）
int main(void) {
    int arr[] = {4, 5, 6, 7, 0, 1, 2};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("旋转数组：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n\n");

    printf("search_rotated(0) → 位置 %d（期望 4）\n", search_rotated(arr, n, 0));
    printf("search_rotated(4) → 位置 %d（期望 0）\n", search_rotated(arr, n, 4));
    printf("search_rotated(2) → 位置 %d（期望 6）\n", search_rotated(arr, n, 2));
    printf("search_rotated(3) → 位置 %d（未找到）\n", search_rotated(arr, n, 3));

    return 0;
}
