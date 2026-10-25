#include <stdio.h>

/*
 * 判断载重量 capacity 是否能在 D 天内运完所有包裹。
 * 返回 1：可以运完
 * 返回 0：不能运完
 */
int can_finish(int weights[], int n, int D, long long capacity) {
    int days = 1;
    long long current = 0;

    for (int i = 0; i < n; i++) {
        if ((long long)weights[i] > capacity) {
            return 0;
        }

        if (current + weights[i] > capacity) {
            days++;
            current = 0;

            if (days > D) {
                return 0;
            }
        }

        current += weights[i];
    }

    return 1;
}

/*
 * 求在 D 天内按顺序运完包裹所需的最小载重量。
 */
long long ship_within_days(int weights[], int n, int D) {
    long long left = 0;
    long long right = 0;

    for (int i = 0; i < n; i++) {
        if (weights[i] > left) {
            left = weights[i];      /* 下界：至少装得下最重包裹 */
        }
        right += weights[i];        /* 上界：一天全部运完 */
    }

    while (left < right) {
        long long mid = left + (right - left) / 2;

        if (can_finish(weights, n, D, mid)) {
            right = mid;            /* mid 可行，继续尝试更小载重量 */
        } else {
            left = mid + 1;         /* mid 不可行，只能增大载重量 */
        }
    }

    return left;
}

int main(void) {
    int weights[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    int n = sizeof(weights) / sizeof(weights[0]);
    int D = 5;

    printf("最小载重量：%lld\n", ship_within_days(weights, n, D));
    return 0;
}
