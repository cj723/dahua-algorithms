#include <stdio.h>
#include <stdlib.h>

/*
 * 计数排序
 * arr：待排序数组
 * n：数组长度
 * k：数据范围（最大值，假设元素在 0 到 k 之间）
 * 返回：排序后的新数组（需要调用者释放内存）
 */

int* counting_sort(int arr[], int n, int k) {
    /* 第一步：创建计数数组，初始化为 0 */
    int *count = (int *)calloc(k + 1, sizeof(int));
    if (!count) return NULL;
    
    /* 第二步：唱票！统计每个值出现的次数 */
    /* 就像选举时，拿起每张选票，往对应候选人的盒子里扔 */
    for (int i = 0; i < n; i++) {
        if (arr[i] < 0 || arr[i] > k) {
            free(count);
            return NULL;
        }
        count[arr[i]]++;
    }
    
    /* 第三步：根据计数结果，按顺序输出 */
    int *result = (int *)malloc(n * sizeof(int));
    if (!result) {
        free(count);
        return NULL;
    }
    
    int idx = 0;
    for (int i = 0; i <= k; i++) {
        /* 值为 i 的元素有 count[i] 个，全部放到结果数组里 */
        while (count[i] > 0) {
            result[idx++] = i;
            count[i]--;
        }
    }
    
    free(count);
    return result;
}

int main(void) {
    /* 模拟一次选举投票：0 = 小明，1 = 小红，2 = 小刚 */
    int votes[] = {2, 0, 1, 2, 1, 0, 2, 1, 0, 0};
    int n = sizeof(votes) / sizeof(votes[0]);
    
    printf("投票结果（排序前）：");
    for (int i = 0; i < n; i++) {
        printf("%d ", votes[i]);
    }
    printf("\n");
    
    int *sorted = counting_sort(votes, n, 2);
    if (sorted == NULL) {
        printf("排序失败：输入值必须在 0 到 2 之间。\n");
        return 1;
    }
    
    printf("统计结果（排序后）：");
    for (int i = 0; i < n; i++) {
        printf("%d ", sorted[i]);
    }
    printf("\n");
    
    free(sorted);
    return 0;
}
