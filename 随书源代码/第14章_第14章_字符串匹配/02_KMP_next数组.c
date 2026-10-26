#include <stdio.h>
#include <string.h>

/* 构建 next 数组 */
void build_next(const char *pattern, int *next, int m) {
    next[0] = -1;
    int i = 0, j = -1;
    
    while (i < m - 1) {
        if (j == -1 || pattern[i] == pattern[j]) {
            i++;
            j++;
            next[i] = j;
        } else {
            j = next[j];  /* 回退！这里用到了已经算好的 next 值 */
        }
    }
}

/* 测试：构建 KMP next 数组 */
int main(void) {
    char pattern[] = "ABABCABAB";
    int m = (int)strlen(pattern);
    int next[100];

    build_next(pattern, next, m);

    printf("模式串：%s\n", pattern);
    printf("next 数组：");
    for (int i = 0; i < m; i++) printf("%d ", next[i]);
    printf("\n\n说明：next[i] 表示 pattern[0..i - 1] 的最长相同前后缀长度\n");
    printf("next[0] = -1 是哨兵，匹配时遇到 next[j] = -1 则 i++、j++\n");

    return 0;
}
