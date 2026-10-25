#include <stdio.h>

int length_of_lis(int nums[], int n) {
    if (n <= 0) {
        return 0;
    }

    int dp[n];  /* VLA，需要 C99 支持；工程中建议用 malloc */
    int maxLen = 1;

    /* 每个元素自身就是一个长度为 1 的子序列 */
    for (int i = 0; i < n; i++) {
        dp[i] = 1;
    }

    /* 从 1 开始：dp[0] = 1 是初始值（单个元素的最长递增子序列长度为 1） */
    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (nums[j] < nums[i]) {
                if (dp[j] + 1 > dp[i]) {
                    dp[i] = dp[j] + 1;
                }
            }
        }
        if (dp[i] > maxLen) {
            maxLen = dp[i];
        }
    }

    return maxLen;
}

int main(void) {
    int nums[] = {10, 9, 2, 5, 3, 7, 101, 18};
    int n = sizeof(nums) / sizeof(nums[0]);
    printf("LIS 长度：%d\n", length_of_lis(nums, n));  /* 输出 4 */
    return 0;
}
