/* 双指针（左右指针）：有序数组两数之和 */
/* 类比：两个人从走廊两头往中间走 */
#include <stdio.h>

/* 在有序数组中找到两个数，使它们的和等于target */
/* 返回两个数的下标，存入result数组 */
/* 如果找不到，返回0 */
int two_sum_sorted(int nums[], int n, int target, int result[2]) {
    int left = 0;         /* 左指针，从头开始 */
    int right = n - 1;    /* 右指针，从尾开始 */
    
    while (left < right) {  /* 两个指针还没相遇 */
        long long sum = (long long)nums[left] + nums[right];
        
        if (sum == target) {
            /* 找到了！ */
            result[0] = left;
            result[1] = right;
            return 1;  /* 返回成功 */
        } else if (sum < target) {
            /* 和太小了，需要更大的数 */
            /* 数组是升序的，left++会让和变大 */
            left++;
        } else {
            /* 和太大了，需要更小的数 */
            /* right--会让和变小 */
            right--;
        }
    }
    
    return 0;  /* 没找到 */
}

int main() {
    int nums[] = {2, 7, 11, 15};
    int n = 4;
    int target = 9;
    int result[2];
    
    if (two_sum_sorted(nums, n, target, result)) {
        printf("下标： [%d, %d]\n", result[0], result[1]);
        /* 输出： [0, 1] */
    } else {
        printf("没找到\n");
    }
    
    return 0;
}
