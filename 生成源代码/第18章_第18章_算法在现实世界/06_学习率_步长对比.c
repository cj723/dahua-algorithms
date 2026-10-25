#include <stdio.h>

/*
 * 学习率对比：同一个函数、同一个起点，
 * 学习率不同，下降轨迹会完全不同。
 */

double f(double x) { return (x - 3) * (x - 3); }      /* f(x) = (x - 3)^2，最小值在 x = 3 */
double grad(double x) { return 2 * (x - 3); }         /* 导数 f'(x) = 2(x - 3) */

/* 梯度下降：对比合适的学习率 vs 太大的学习率 */
void gd(double lr, const char* label) {
    double x = 0;
    printf("%s (lr=%.2f): ", label, lr);
    for (int i = 0; i < 12; i++) {
        x = x - lr * grad(x);
    }
    printf("12 步后 x=%.4f，f(x)=%.4f\n", x, f(x));
}

int main(void) {
    gd(0.1, "合适的学习率");   /* 平稳收敛到 3 */
    printf("\n");
    gd(1.1, "太大的学习率");   /* 震荡并发散 */
    return 0;
}
