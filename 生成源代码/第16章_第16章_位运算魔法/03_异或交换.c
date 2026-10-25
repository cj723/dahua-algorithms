#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 不使用临时变量，交换 a 和 b 的值 */
/* 利用异或的性质：a ^ a = 0, a ^ 0 = a */
/* 类比：两个人交换礼物，用纸箱中转——先放进去，再拿出来 */
void swap(int *a, int *b) {
    if (a == b) return;  /* 防止同一个地址异或自己变成 0 */
    *a = *a ^ *b;        /* 第 1 步：a 变成“a 和 b 的异或值” */
    *b = *a ^ *b;        /* 第 2 步：b = (a ^ b) ^ b = a，b 拿到了原来的 a */
    *a = *a ^ *b;        /* 第 3 步：a = (a ^ b) ^ a = b，a 拿到了原来的 b */
}


/* ===== 自动生成的测试入口 ===== */
int main(void) {
    int a = 5;
    int b = 3;

    printf("交换前：a=%d, b=%d\n", a, b);
    swap(&a, &b);
    printf("交换后：a=%d, b=%d\n", a, b);

    return 0;
}
