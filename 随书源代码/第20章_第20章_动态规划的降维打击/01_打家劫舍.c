#include <stdio.h>

static int max_value(int a, int b) {
    return a > b ? a : b;
}

int rob(int *nums, int numsSize) {
    if (numsSize <= 0) return 0;
    if (numsSize == 1) return nums[0];

    int prev2 = 0;        /* 对应 dp[i - 2] */
    int prev1 = nums[0];  /* 对应 dp[i - 1] */
    int current = 0;      /* 对应 dp[i] */

    for (int i = 1; i < numsSize; i++) {
        current = max_value(prev1, prev2 + nums[i]);

        /* 历史向前滚动一格 */
        prev2 = prev1;
        prev1 = current;
    }

    return prev1;
}


// 测试：打家劫舍（滚动变量优化）
int main(void) {
    int houses1[] = {1, 2, 3, 1};
    printf("房屋[1,2,3,1] → 最高：%d（期望 4）\n",
           rob(houses1, 4));

    int houses2[] = {2, 7, 9, 3, 1};
    printf("房屋[2,7,9,3,1] → 最高：%d（期望 12）\n",
           rob(houses2, 5));

    printf("\n说明：只用 prev2, prev1, current 三个变量，\n");
    printf("空间从 O(n) 降到 O(1)\n");

    return 0;
}
