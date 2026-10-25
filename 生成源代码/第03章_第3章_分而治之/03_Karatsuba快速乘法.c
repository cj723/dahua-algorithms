#include <stdio.h>
#include <math.h>

/* 求较大值 */
/* 教学版写法：使用 log10。真实工程中不能用浮点函数处理大整数。 */
long long max(long long a, long long b) {
    return (a > b) ? a : b;
}

/* Karatsuba 乘法 */
long long karatsuba(long long x, long long y) {
    /* 小规模直接算（终止条件） */
    if (x < 10 || y < 10)
        return x * y;

    /* 计算位数 */
    /* 注意：log10 有浮点精度风险，大数可能出错。工程建议用循环计算位数 */
    long long n = max(
        (long long)log10(x) + 1,
        (long long)log10(y) + 1
    );

    /* 对半分（向上取整） */
    long long half = (n + 1) / 2;
    /* 教学版写法：使用 pow。数值过大时浮点数会丢失精度。 */
    long long power = (long long)pow(10, half);

    /* 拆分 */
    long long a = x / power;   /* x 的高位 */
    long long b = x % power;   /* x 的低位 */
    long long c = y / power;   /* y 的高位 */
    long long d = y % power;   /* y 的低位 */

    /* 递归计算三次乘法 */
    long long ac = karatsuba(a, c);
    long long bd = karatsuba(b, d);
    long long ad_bc = karatsuba(a + b, c + d) - ac - bd;

    /* 合并结果 */
    /* X × Y = ac × 10^(2×half) + (ad+bc) × 10^half + bd */
    return ac * (long long)pow(10, 2 * half)
         + ad_bc * power
         + bd;
}

int main(void) {
    long long x = 1234, y = 5678;

    printf("传统乘法：%lld\n", x * y);
    printf("Karatsuba：%lld\n", karatsuba(x, y));

    return 0;
}
