#include <stdio.h>

int interpolation_search(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    
    while (left <= right && target >= arr[left] && target <= arr[right]) {
        /* 防止除零（如果 arr[left] == arr[right]，说明这一段全相等） */
        if (arr[left] == arr[right]) {
            if (arr[left] == target) return left;
            else return -1;
        }
        
        /* 插值公式估算位置 */
        int mid = left + (int)(
            ((long long)target - arr[left]) * (right - left)
            / ((long long)arr[right] - arr[left])
        );
        
        if (arr[mid] == target) {
            return mid;
        } else if (arr[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    
    return -1;
}


// 测试：插值查找（适用于均匀分布的有序数组）
int main(void) {
    int arr[] = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("数组：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n\n");

    // 均匀分布，插值查找很高效
    printf("interpolation_search(30) → 位置 %d（期望 2）\n", interpolation_search(arr, n, 30));
    printf("interpolation_search(80) → 位置 %d（期望 7）\n", interpolation_search(arr, n, 80));
    printf("interpolation_search(10) → 位置 %d（期望 0）\n", interpolation_search(arr, n, 10));
    printf("interpolation_search(55) → 位置 %d（未找到）\n", interpolation_search(arr, n, 55));

    return 0;
}
