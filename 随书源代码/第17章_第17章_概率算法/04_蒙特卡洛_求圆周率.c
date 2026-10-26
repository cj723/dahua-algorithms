/* 蒙特卡洛方法求圆周率 π */
/* 类比：往正方形里扔飞镖，统计落在圆内的比例 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

/* 蒙特卡洛求 π */
/* 参数 total_points：总共扔多少个飞镖 */
/* 返回值：估算的 π 值 */
double monte_carlo_pi(int total_points) {
    if (total_points <= 0) {
        return 0.0;  /* 参数不合法时返回 0，避免除以 0 */
    }

    int inside_circle = 0;  /* 落在圆内的飞镖数 */

    for (int i = 0; i < total_points; i++) {
        /* 生成 [-1, 1] 之间的随机坐标 */
        /* rand() / (double)RAND_MAX 生成 [0, 1] 之间的随机数 */
        /* 乘以 2 再减 1，映射到 [-1, 1] */
        double x = 2.0 * rand() / (double)RAND_MAX - 1.0;  /* 用 (double) 显式转换，避免误以为是整数除法 */
        double y = 2.0 * rand() / (double)RAND_MAX - 1.0;

        /* 计算到圆心距离的平方 */
        double dist_sq = x * x + y * y;

        /* 如果距离平方 <= 1，说明在圆内（半径为 1 的圆） */
        if (dist_sq <= 1.0) {
            inside_circle++;  /* 落在圆内，计数 + 1 */
        }
    }

    /* π ≈ 4 × (圆内点数 / 总点数) */
    /* 蒙特卡洛误差大约按 O(1/sqrt(n)) 缩小，误差到 1e-3 往往要 1e6 量级采样 */
    return 4.0 * inside_circle / total_points;
}

int main(void) {
    int trials[] = {100, 1000, 10000, 100000, 1000000};
    int num_trials = 5;

    srand((unsigned int)time(NULL));  /* 初始化随机种子 */

    printf("蒙特卡洛方法求 π：\n");
    printf("投掷次数\t估算值\t\t误差\n");
    printf("─────────────────────────────────────\n");

    for (int i = 0; i < num_trials; i++) {
        double pi_estimate = monte_carlo_pi(trials[i]);
        double error = pi_estimate - 3.14159265358979323846;
        if (error < 0) error = -error;  /* 取绝对值 */
        printf("%d\t\t%.6f\t\t%.6f\n", trials[i], pi_estimate, error);
    }

    return 0;
}
