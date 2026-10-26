#include <stdio.h>
#include <stdlib.h>

/* 活动结构体 */
typedef struct {
    int id;         /* 活动编号 */
    int start;      /* 开始时间 */
    int end;        /* 结束时间 */
} Activity;

/* 比较函数：按结束时间升序排列 */
int compare(const void *a, const void *b) {
    const Activity *x = (const Activity *)a;
    const Activity *y = (const Activity *)b;
    if (x->end != y->end) return (x->end > y->end) - (x->end < y->end);
    return (x->start > y->start) - (x->start < y->start);
}

/* 贪心求解活动选择 */
void activity_selection(Activity activities[], int n) {
    if (n <= 0) {
        printf("没有可安排的活动\n");
        return;
    }

    /* 第一步：按结束时间排序 */
    qsort(activities, n, sizeof(Activity), compare);

    printf("选择的活动序列：\n");

    /* 第二步：总是选第一个（结束最早的） */
    int count = 1;
    int last_end = activities[0].end;
    printf("  活动 %d：[%d, %d)\n",
           activities[0].id, activities[0].start, activities[0].end);

    /* 第三步：贪心选择后续活动 */
    for (int i = 1; i < n; i++) {
        if (activities[i].start >= last_end) {
            printf("  活动 %d：[%d, %d)\n",
                   activities[i].id, activities[i].start, activities[i].end);
            last_end = activities[i].end;
            count++;
        }
    }

    printf("总共可安排 %d 场活动\n", count);
}

int main(void) {
    Activity activities[] = {
        {1, 1, 4}, {2, 3, 5}, {3, 0, 6}, {4, 5, 7},
        {5, 3, 9}, {6, 5, 9}, {7, 6, 10}, {8, 8, 11},
        {9, 8, 12}, {10, 2, 14}, {11, 12, 16}
    };
    int n = sizeof(activities) / sizeof(activities[0]);

    activity_selection(activities, n);
    return 0;
}
