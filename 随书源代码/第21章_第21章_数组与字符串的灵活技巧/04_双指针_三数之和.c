/* 三数之和：找出所有和为0的三元组 */
/* 固定一个数 + 双指针找另外两个 */
#include <stdio.h>
#include <stdlib.h>

/* 比较函数，用于qsort排序 */
int compare(const void *a, const void *b) {
    int x = *(int *)a, y = *(int *)b;
    if (x < y) return -1;
    if (x > y) return 1;
    return 0;
}

/* 三数之和 */
/* 结果存入results数组，返回找到的三元组个数 */
/* max_results用于防止结果数组越界 */
int three_sum(int nums[], int n, int results[][3], int max_results) {
    int count = 0;  /* 结果计数 */
    
    /* 第1步：排序 */
    qsort(nums, n, sizeof(int), compare);
    
    /* 第2步：遍历每个元素作为第一个数 */
    for (int i = 0; i < n - 2; i++) {
        /* 剪枝：如果当前数>0，后面的数都更大，不可能和为0 */
        if (nums[i] > 0) break;
        
        /* 跳过重复的第一个数 */
        if (i > 0 && nums[i] == nums[i - 1]) continue;
        
        /* 第3步：双指针找另外两个数 */
        int left = i + 1;       /* 左指针从i+1开始 */
        int right = n - 1;      /* 右指针从末尾开始 */
        
        while (left < right) {
            /* 三个int连加极易整数溢出。严谨做法是转long long再判断。
             * 只需把第一个操作数强转为long long，后两个会自动提升，避免中间结果溢出。
             * 面试白板上写出这种防溢出细节，面试官会对你的工程素养刮目相看。 */
            long long sum = (long long)nums[i] + (long long)nums[left] + (long long)nums[right];
            
            if (sum == 0) {
                /* 找到了一个三元组 */
                if (count < max_results) {
                    results[count][0] = nums[i];
                    results[count][1] = nums[left];
                    results[count][2] = nums[right];
                    count++;
                } else {
                    return count;  /* 结果数组满了，避免越界 */
                }
                
                /* 跳过重复的左指针元素 */
                while (left < right && nums[left] == nums[left + 1]) left++;
                /* 跳过重复的右指针元素 */
                while (left < right && nums[right] == nums[right - 1]) right--;
                
                /* 同时移动两个指针 */
                left++;
                right--;
            } else if (sum < 0) {
                /* 和太小，左指针右移 */
                left++;
            } else {
                /* 和太大，右指针左移 */
                right--;
            }
        }
    }
    
    return count;
}

int main() {
    int nums[] = {-1, 0, 1, 2, -1, -4};
    int n = 6;
    int results[100][3];  /* 存放结果 */
    int max_results = sizeof(results) / sizeof(results[0]);
    int count, i;
    
    count = three_sum(nums, n, results, max_results);
    
    printf("和为0的三元组：\n");
    for (i = 0; i < count; i++) {
        printf("[%d, %d, %d]\n", results[i][0], results[i][1], results[i][2]);
    }
    
    return 0;
}
