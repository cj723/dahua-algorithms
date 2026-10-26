#include <stdio.h>

int lowbit(int x) {
    return x & (-x);
}


// 演示 lowbit 运算：取一个数二进制中最低位的 1
int main(void) {
    printf("lowbit(x) = x & (-x)，取 x 二进制最低位的 1 所代表的值\n\n");
    printf("lowbit(6)  = %d  （6=0b110,  最低位 1 在 2^1 位）\n", lowbit(6));
    printf("lowbit(8)  = %d  （8=0b1000, 最低位 1 在 2^3 位）\n", lowbit(8));
    printf("lowbit(12) = %d （12=0b1100, 最低位 1 在 2^2 位）\n", lowbit(12));
    printf("lowbit(7)  = %d  （7=0b111,  最低位 1 在 2^0 位）\n", lowbit(7));
    printf("\n树状数组中，c[x] 管理从 x - lowbit(x) + 1 到 x 的区间\n");

    return 0;
}