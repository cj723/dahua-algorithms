#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MIN3(a, b, c) MIN(MIN(a, b), c)

int min_distance(char *word1, char *word2) {
    int m = (int)strlen(word1);
    int n = (int)strlen(word2);

    /* 一次性分配连续的一维内存来模拟二维数组（工程规范写法） */
    /* dp[i][j] 对应 dp[i * (n + 1) + j] */
    int cols = n + 1;
    int *dp = (int *)malloc((m + 1) * cols * sizeof(int));
    if (dp == NULL) {
        return -1;  /* 表示内存分配失败 */
    }

    /* 初始化边界：空串变成目标串，只能一个一个插入 */
    for (int i = 0; i <= m; i++) dp[i * cols + 0] = i;  /* 删除操作 */
    for (int j = 0; j <= n; j++) dp[0 * cols + j] = j;  /* 插入操作 */

    /* 填表 */
    for (int i = 1; i <= m; i++) {
        for (int j = 1; j <= n; j++) {
            if (word1[i - 1] == word2[j - 1]) {
                dp[i * cols + j] = dp[(i - 1) * cols + (j - 1)];
            } else {
                dp[i * cols + j] = 1 + MIN3(
                    dp[(i - 1) * cols + j],        /* 删除 */
                    dp[i * cols + (j - 1)],        /* 插入 */
                    dp[(i - 1) * cols + (j - 1)]   /* 替换 */
                );
            }
        }
    }

    int result = dp[m * cols + n];
    free(dp);
    return result;
}

int main(void) {
    char word1[] = "horse";
    char word2[] = "ros";
    printf("编辑距离：%d\n", min_distance(word1, word2));  /* 输出 3 */
    return 0;
}
