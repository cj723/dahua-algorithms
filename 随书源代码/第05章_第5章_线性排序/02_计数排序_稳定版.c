#include <stdio.h>
#include <stdlib.h>

/*
 * 稳定版计数排序
 * 算法多走一步：先累加 count 数组，得到每个值的“结束位置”
 * 然后从后往前遍历原数组，把每个元素放到正确位置
 */

int* counting_sort_stable(int arr[], int n, int k) {
    int *count = (int *)calloc(k + 1, sizeof(int));
    int *result = (int *)malloc(n * sizeof(int));
    if (!count || !result) {
        free(count);
        free(result);
        return NULL;
    }
    
    /* 唱票 */
    for (int i = 0; i < n; i++) {
        if (arr[i] < 0 || arr[i] > k) {
            free(count);
            free(result);
            return NULL;
        }
        count[arr[i]]++;
    }
    
    /* 累加：count[i] 变成“值 <= i 的元素总个数” */
    /* 即：值为 i 的元素在结果数组中的右开边界（最后一个值为 i 的元素落在下标 count[i] - 1 处） */
    for (int i = 1; i <= k; i++) {
        count[i] += count[i - 1];
    }
    
    /* 从后往前遍历（关键！这样才能保证稳定性） */

    /* 就像排队时，后来的人站到队伍末尾 */

    for (int i = n - 1; i >= 0; i--) {
        result[count[arr[i]] - 1] = arr[i];
        count[arr[i]]--;
    }
    
    free(count);
    return result;
}


// 测试：稳定版计数排序
int main(void) {
    // 用学生成绩演示稳定性：成绩相同的学生，排序后保持原顺序
    // 数组值代表分数，下标代表"交卷先后"（隐含在原数组顺序中）
    int scores[] = {2, 0, 1, 2, 1, 0, 2, 1, 0, 0};
    int n = sizeof(scores) / sizeof(scores[0]);

    printf("原始（按交卷顺序）：");
    for (int i = 0; i < n; i++) printf("%d ", scores[i]);
    printf("\n");

    int *sorted = counting_sort_stable(scores, n, 2);
    if (sorted == NULL) {
        printf("排序失败：输入值必须在 0 到 2 之间。\n");
        return 1;
    }

    printf("稳定排序后：        ");
    for (int i = 0; i < n; i++) printf("%d ", sorted[i]);
    printf("\n");

    printf("说明：同为0分的学生，原顺序是下标1→5→8→9，排序后仍是这个顺序\n");

    free(sorted);
    return 0;
}
