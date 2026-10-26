#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 统计整数 n 的二进制表示中有多少个 1 */
/* 思路：每次 n & (n - 1) 清掉最低位的 1，计数 + 1 */
/* 类比：拔萝卜——每次拔掉最矮的那个萝卜，数拔了几次 */

int count_bits(unsigned int n) {
    int count = 0;          /* 计数器初始化为 0 */
    while (n != 0) {        /* 只要 n 不为 0，说明还有 1 */
        n = n & (n - 1);    /* 清掉最低位的 1 */
        count++;            /* 计数加 1 */
    }
    return count;           /* 返回 1 的个数 */
}


// 测试：Brian Kernighan 算法统计二进制中 1 的个数
int main(void) {
    printf("Brian Kernighan 算法：每次 n & (n - 1) 消掉最低位的 1\n\n");
    printf("count_bits(0)  = %d  （0b0）\n", count_bits(0));
    printf("count_bits(7)  = %d  （0b111）\n", count_bits(7));
    printf("count_bits(15) = %d （0b1111）\n", count_bits(15));
    printf("count_bits(42) = %d （0b101010）\n", count_bits(42));
    printf("\n时间复杂度 = O(1 的个数)，比逐位检查的 O(log n) 更快\n");

    return 0;
}
