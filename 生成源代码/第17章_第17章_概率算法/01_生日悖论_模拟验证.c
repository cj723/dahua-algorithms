/* 生日悖论蒙特卡洛验证 */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

int main(void) {
    int n = 50;          /* 屋子里的人数 */
    int trials = 100000; /* 重复实验次数 */
    int collisions = 0;  /* 出现重复生日的次数 */

    srand((unsigned int)time(NULL));

    for (int t = 0; t < trials; t++) {
        int days[365] = {0}; /* 一年365天 */
        int found = 0;
        for (int i = 0; i < n; i++) {
            int birthday = rand() % 365;
            if (days[birthday]) { found = 1; break; }
            days[birthday] = 1;
        }
        if (found) collisions++;
    }

    printf("%d 人中出现重复生日的概率：%.1f%%\n",
           n, 100.0 * collisions / trials);
    /* 输出大约 97%! */
    return 0;
}
