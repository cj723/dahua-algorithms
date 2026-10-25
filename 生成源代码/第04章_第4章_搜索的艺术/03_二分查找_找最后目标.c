#include <stdio.h>

/* 找最后一个等于 target 的位置 */
int find_last(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    int result = -1;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;
        
        if (arr[mid] == target) {
            result = mid;       /* 记住这个位置 */
            left = mid + 1;     /* 继续往右找，看看后面有没有更晚出现的 */
        } else if (arr[mid] < target) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    
    return result;
}


// 测试：找最后一个出现的位置（数组含重复元素）
int main(void) {
    int arr[] = {1, 2, 2, 2, 3, 3, 4, 5, 5, 5, 5, 6};
    int n = sizeof(arr) / sizeof(arr[0]);

    printf("数组：");
    for (int i = 0; i < n; i++) printf("%d ", arr[i]);
    printf("\n\n");

    // 重复元素：找最后一个出现位置
    printf("find_last(2) → 位置 %d（期望 3）\n", find_last(arr, n, 2));
    printf("find_last(5) → 位置 %d（期望 10）\n", find_last(arr, n, 5));
    printf("find_last(3) → 位置 %d（期望 5）\n", find_last(arr, n, 3));

    // 不存在的元素
    printf("find_last(9) → 位置 %d（未找到）\n", find_last(arr, n, 9));

    return 0;
}
