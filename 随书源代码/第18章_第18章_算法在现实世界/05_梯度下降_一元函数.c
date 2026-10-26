#include <stdio.h>
#include <math.h>

/*
 * 梯度下降求解 y = (x-3)^2 的最小值
 *
 * 类比：你在雾里下山
 * 目标：找到最低点（x = 3）
 * 方法：感受坡度，往下走
 */

double cost(double x) {
    return (x - 3) * (x - 3);  /* 损失函数：一个开口向上的抛物线 */
}

double gradient(double x) {
    return 2 * (x - 3);  /* 梯度：损失函数的导数 */
}

int main(void) {
    double x = 0.0;           /* 起始位置（随机的，可能很远） */
    double learning_rate = 0.1; /* 学习率：每步走多大 */
    int max_steps = 100;      /* 最多走 100 步 */

    printf("=== 梯度下降演示 ===\n");
    printf("目标：找到 y=(x-3)^2 的最小值（答案是 x = 3）\n\n");
    printf("步骤    x值       损失值      梯度\n");
    printf("----------------------------------------\n");

    for (int i = 0; i < max_steps; i++) {
        double loss = cost(x);
        double grad = gradient(x);

        if (i % 10 == 0) {
            printf("%3d    %6.4f    %6.4f    %6.4f\n", i, x, loss, grad);
        }

        /* 梯度下降核心：往梯度的反方向走 */
        x = x - learning_rate * grad;

        /* 如果梯度足够小，说明已经到了最低点 */
        if (fabs(grad) < 0.0001) break;
    }

    printf("\n找到最优解： x = %.4f (真实答案： 3.0)\n", x);
    printf("最低损失： %.6f\n", cost(x));

    return 0;
}
