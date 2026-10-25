/* 差分数组：快速对区间进行批量加减操作 */
/* 类比：每天的收支记录——修改收支比修改余额方便 */

#include <stdio.h>

/* 构建差分数组 */
/* diff[i] = nums[i] - nums[i-1] */
/* diff[0] = nums[0] */
void build_diff_array(int nums[], int n, long long diff[]) {
    if (n <= 0) return;
    diff[0] = nums[0];
    for (int i = 1; i < n; i++) {
        diff[i] = (long long)nums[i] - nums[i - 1];
    }
}

/* 对区间[left, right]的所有元素加上val */
/* 只需要修改diff[left]和diff[right+1]两个位置！ */
void range_add(long long diff[], int n, int left, int right, long long val) {
    if (left < 0 || right >= n || left > right) return;  /* 简单防御 */
    diff[left] += val;           /* left位置开始加val */
    if (right + 1 < n) {
        diff[right + 1] -= val;  /* right+1位置减去val，抵消前面的加 */
    }
}

/* 从差分数组还原原始数组（对差分数组求前缀和） */
void restore_array(long long diff[], int n, long long result[]) {
    if (n <= 0) return;
    result[0] = diff[0];
    for (int i = 1; i < n; i++) {
        result[i] = result[i - 1] + diff[i];
    }
}

int main() {
    int nums[] = {1, 2, 3, 4, 5};
    int n = 5;
    long long diff[5];
    long long result[5];
    
    build_diff_array(nums, n, diff);
    
    /* 对区间[1, 3]的所有元素加10 */
    /* 原始数组变成：[1, 12, 13, 14, 5] */
    range_add(diff, n, 1, 3, 10);
    
    /* 还原数组 */
    restore_array(diff, n, result);
    
    printf("修改后： ");
    for (int i = 0; i < n; i++) {
        printf("%lld ", result[i]);
    }
    printf("\n");
    /* 输出： 1 12 13 14 5 */

    
    return 0;
}
