#include <stdio.h>
#include <stdlib.h>

/* 在 tails[0..len - 1] 中，找第一个 >= target 的位置 */
int lower_bound(int tails[], int len, int target) {
    int left = 0, right = len;
    while (left < right) {
        int mid = left + (right - left) / 2;
        if (tails[mid] < target) {
            left = mid + 1;
        } else {
            right = mid;
        }
    }
    return left;
}

int length_of_lis_bs(int nums[], int n) {
    if (n <= 0) return 0;

    int *tails = (int *)malloc(n * sizeof(int));
    if (tails == NULL) return 0;

    int len = 0;

    for (int i = 0; i < n; i++) {
        int pos = lower_bound(tails, len, nums[i]);
        tails[pos] = nums[i];
        if (pos == len) {
            len++;
        }
    }

    free(tails);
    return len;
}

int main(void) {
    int nums[] = {10, 9, 2, 5, 3, 7, 101, 18};
    int n = sizeof(nums) / sizeof(nums[0]);

    printf("LIS 长度（二分优化）：%d\n", length_of_lis_bs(nums, n));
    return 0;
}
