#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 判断正整数 n 是否是 2 的幂 */
/* 思路：2 的幂只有一个 1，n & (n - 1) 应该等于 0 */
/* 类比：2 的幂就像独行侠——只携带一个“1” */
int is_power_of_two(unsigned int n) {
    return n != 0 && ((n & (n - 1)) == 0);
}


// 测试：判断一个数是否是 2 的幂
int main(void) {
    printf("判断依据：2 的幂的二进制只有一个 1，n & (n - 1) == 0\n\n");
    printf("is_power_of_two(1)  = %d （0b1）\n", is_power_of_two(1));
    printf("is_power_of_two(2)  = %d （0b10）\n", is_power_of_two(2));
    printf("is_power_of_two(8)  = %d （0b1000）\n", is_power_of_two(8));
    printf("is_power_of_two(10) = %d （0b1010——不是 2 的幂）\n", is_power_of_two(10));
    printf("is_power_of_two(0)  = %d （0 不是 2 的幂）\n", is_power_of_two(0));

    return 0;
}
