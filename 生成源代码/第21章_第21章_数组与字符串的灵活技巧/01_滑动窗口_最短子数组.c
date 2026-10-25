/* 滑动窗口：长度最小的子数组 */
/* 总和>=target的最短连续子数组长度 */
/* 类比：火车车窗看风景——窗口不断滑动，找到最佳视角 */
#include <stdio.h>
#include <limits.h>

/* 返回总和>=target的最短子数组长度 */
/* 如果不存在返回0 */
int min_subarray_len(long long target, int nums[], int n) {
    int left = 0;              /* 窗口左边界 */
    long long window_sum = 0;  /* 当前窗口内的元素和，用long long防溢出 */
    int min_len = INT_MAX;     /* 记录最小长度，初始化为最大值 */
    
    /* right从0开始，不断向右扩展 */
    for (int right = 0; right < n; right++) {
        /* 第1步：把新元素加入窗口 */
        window_sum += nums[right];
        
        /* 第2步：当窗口和>=target时，尝试收缩左边界 */
        while (window_sum >= target) {
            /* 当前窗口已经满足条件，先更新最小长度 */
            int current_len = right - left + 1;
            if (current_len < min_len) {
                min_len = current_len;
            }
            /* 再收缩左边界：把左边的元素移出窗口 */
            window_sum -= nums[left];
            left++;
        }
        /* 第3步：如果窗口和<target，继续扩展right（for循环自动处理） */
    }
    
    /* 如果没找到，返回0 */
    return (min_len == INT_MAX) ? 0 : min_len;
}

int main() {
    int nums[] = {2, 3, 1, 2, 4, 3};
    int n = 6;
    long long target = 7;
    
    int result = min_subarray_len(target, nums, n);
    printf("总和>= %lld 的最短子数组长度： %d\n", target, result);
    /* 输出： 2 */
    
    return 0;
}
