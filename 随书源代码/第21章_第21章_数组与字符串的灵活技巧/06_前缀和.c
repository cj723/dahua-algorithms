/* 前缀和：快速查询任意区间的和 */
/* 类比：记账——每天的余额就是前缀和 */
#include <stdio.h>

/* 构建前缀和数组 */
/* prefix_sum[i] = nums[0] + nums[1] + ... + nums[i-1] */
/* 注意：prefix_sum[0] = 0，方便计算 */
void build_prefix_sum(int nums[], int n, long long prefix_sum[]) {
    prefix_sum[0] = 0;  /* 哨兵：前0个元素的和是0 */
    for (int i = 0; i < n; i++) {
        prefix_sum[i + 1] = prefix_sum[i] + nums[i];
    }
}

/* 查询区间[left, right]的和（闭区间） */
/* 时间复杂度：$O(1)$！ */
long long range_sum(long long prefix_sum[], int left, int right) {
    return prefix_sum[right + 1] - prefix_sum[left];
}

int main() {
    int nums[] = {1, 2, 3, 4, 5};
    int n = 5;
    long long prefix_sum[6];  /* n+1个元素，第0个是哨兵 */
    
    build_prefix_sum(nums, n, prefix_sum);
    
    /* 查询各种区间的和 */
    printf("区间[0, 2]的和： %lld\n", range_sum(prefix_sum, 0, 2));  /* 1+2+3=6 */
    printf("区间[1, 3]的和： %lld\n", range_sum(prefix_sum, 1, 3));  /* 2+3+4=9 */
    printf("区间[2, 4]的和： %lld\n", range_sum(prefix_sum, 2, 4));  /* 3+4+5=12 */
    
    return 0;
}
