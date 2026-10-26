#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 构建 next 数组（用于对比） */
void build_next(const char *pattern, int *next, int m) {
    next[0] = -1;
    int i = 0, j = -1;
    while (i < m - 1) {
        if (j == -1 || pattern[i] == pattern[j]) {
            i++;
            j++;
            next[i] = j;
        } else {
            j = next[j];
        }
    }
}

/* 构建 nextval 数组（KMP 终极优化） */
void build_nextval(const char *pattern, int *nextval, int m) {
    nextval[0] = -1;
    int i = 0, j = -1;
    while (i < m - 1) {
        if (j == -1 || pattern[i] == pattern[j]) {
            i++;
            j++;
            /* 关键区别：如果回退位置的字符和当前位置相同，
             * 回退过去必然再次失配，直接再跳一步 */
            if (pattern[i] != pattern[j]) {
                nextval[i] = j;
            } else {
                nextval[i] = nextval[j];
            }
        } else {
            j = nextval[j];
        }
    }
}

/* 测试：构建 KMP nextval 数组（相比 next 的优化版） */
int main(void) {
    char pattern[] = "ABABCABAB";
    int m = (int)strlen(pattern);
    int nextval[100], next[100];

    build_nextval(pattern, nextval, m);
    build_next(pattern, next, m);

    printf("模式串：    ");
    for (int i = 0; i < m; i++) printf(" %c ", pattern[i]);
    printf("\nnext 数组：  ");
    for (int i = 0; i < m; i++) printf("%2d ", next[i]);
    printf("\nnextval 数组：");
    for (int i = 0; i < m; i++) printf("%2d ", nextval[i]);
    printf("\n\n说明：nextval 在 next 基础上进一步优化——\n");
    printf("如果回退位置的字符与当前相同，直接跳过（避免重复失配）\n");

    return 0;
}
